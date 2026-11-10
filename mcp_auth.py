"""Owner-only OAuth authorization-code + S256 PKCE for the Railway MCP server.

Clients are signed registrations; short-lived codes and hashed token grants are
persisted in the existing private Profile.extra with PostgreSQL row locking.
No API keys, plaintext tokens, new tables, or third-party identity service needed.
"""
import base64
import copy
import hashlib
import hmac
import re
import secrets
import time
from urllib.parse import urlencode, urlsplit

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, url_for
from itsdangerous import BadSignature, URLSafeSerializer, URLSafeTimedSerializer

from models import Profile, db

routes = Blueprint('mcp_oauth', __name__)
SCOPES = ['reading:read', 'drafts:write']
STATE_KEY = 'mcp_oauth'
CODE_TTL, ACCESS_TTL, REFRESH_TTL = 300, 900, 7 * 86400


class OAuthError(ValueError):
    def __init__(self, error, description, status=400):
        self.error, self.description, self.status = error, description, status
        super().__init__(description)


def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def origin():
    value = current_app.config.get('SITE_URL') or request.url_root.rstrip('/')
    parts = urlsplit(value)
    if parts.scheme not in ('https', 'http') or not parts.netloc or parts.username or parts.password:
        raise OAuthError('server_error', '홈페이지 공개 주소 설정을 확인해 주세요.', 503)
    if parts.scheme != 'https' and not current_app.testing:
        raise OAuthError('server_error', 'MCP 연결에는 HTTPS 주소가 필요합니다.', 503)
    return f'{parts.scheme}://{parts.netloc}'


def resource():
    return origin() + '/mcp'


def challenge(error='invalid_token'):
    # ChatGPT requires error details in the tool-level challenge to open linking UI.
    code = 'insufficient_scope' if error == 'insufficient_scope' else 'invalid_token'
    return (f'Bearer resource_metadata="{origin()}/.well-known/oauth-protected-resource/mcp", '
            f'scope="{" ".join(SCOPES)}", error="{code}", '
            'error_description="Sign in to HY ARCHIVE and approve the required permissions"')


def client_signer():
    return URLSafeSerializer(current_app.secret_key, salt='hy-mcp-client-v1')


def refresh_signer():
    return URLSafeTimedSerializer(current_app.secret_key, salt='hy-mcp-refresh-v1')


def loopback_redirect(value):
    try:
        p = urlsplit(value)
        return (p.scheme == 'http' and p.hostname == '127.0.0.1' and not p.username and not p.password
                and not p.query and not p.fragment and (p.port is None or 1 <= p.port <= 65535)
                and re.fullmatch(r'/callback(?:/[A-Za-z0-9_-]+)?', p.path) is not None)
    except (ValueError, TypeError):
        return False


def allowed_redirect(value):
    if not isinstance(value, str) or len(value) > 2048:
        return False
    try:
        p = urlsplit(value)
        return (loopback_redirect(value) or
                (p.scheme == 'https' and p.netloc == 'chatgpt.com' and not p.fragment
                 and (p.path == '/connector_platform_oauth_redirect'
                      or re.fullmatch(r'/connector/oauth/[A-Za-z0-9_-]+', p.path) is not None)))
    except ValueError:
        return False


def redirect_matches(value, registered):
    if not allowed_redirect(value):
        return False
    for candidate in registered:
        if value == candidate:
            return True
        # RFC 8252: native clients choose their loopback listener port at login.
        if loopback_redirect(value) and loopback_redirect(candidate):
            if urlsplit(value).path == urlsplit(candidate).path:
                return True
    return False


def client_metadata(client_id):
    if not isinstance(client_id, str) or len(client_id) > 6000:
        raise OAuthError('invalid_client', '클라이언트 등록을 다시 진행해 주세요.')
    try:
        data = client_signer().loads(client_id)
    except BadSignature:
        raise OAuthError('invalid_client', '등록되지 않은 클라이언트입니다.') from None
    if not isinstance(data, dict) or data.get('v') != 1:
        raise OAuthError('invalid_client', '지원하지 않는 클라이언트입니다.')
    return data


def owner_fingerprint():
    return sha(str(current_app.config.get('ADMIN_USERNAME', '')) + '\n' + str(current_app.config.get('ADMIN_PASSWORD_HASH', '')))


def stored_state(profile):
    return copy.deepcopy((profile.extra or {}).get(STATE_KEY, {'codes': {}, 'grants': {}})) if profile else {'codes': {}, 'grants': {}}


def locked_state():
    profile = Profile.query.order_by(Profile.id).with_for_update().first()
    if profile is None:
        raise OAuthError('server_error', '관리자 소개 정보를 먼저 저장해 주세요.', 503)
    state = stored_state(profile)
    now = time.time()
    state['codes'] = {k: v for k, v in state.get('codes', {}).items() if v['expires'] > now}
    state['grants'] = {k: v for k, v in state.get('grants', {}).items() if v['refresh_expires'] > now}
    return profile, state


def save_state(profile, state):
    profile.extra = {**(profile.extra or {}), STATE_KEY: state}
    db.session.commit()


@routes.after_request
def private_headers(response):
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Referrer-Policy'] = 'same-origin'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


@routes.errorhandler(OAuthError)
def oauth_error(error):
    db.session.rollback()
    return jsonify(error=error.error, error_description=error.description), error.status


@routes.get('/.well-known/oauth-protected-resource')
@routes.get('/.well-known/oauth-protected-resource/mcp')
def protected_resource():
    return jsonify(resource=resource(), authorization_servers=[origin()], scopes_supported=SCOPES,
                   bearer_methods_supported=['header'], resource_name='HY ARCHIVE 독서 기록')


@routes.get('/.well-known/oauth-authorization-server')
def authorization_metadata():
    return jsonify(issuer=origin(), authorization_endpoint=origin() + '/admin/mcp/authorize',
                   token_endpoint=origin() + '/oauth/token', registration_endpoint=origin() + '/oauth/register',
                   revocation_endpoint=origin() + '/oauth/revoke', response_types_supported=['code'],
                   grant_types_supported=['authorization_code', 'refresh_token'],
                   token_endpoint_auth_methods_supported=['none'], code_challenge_methods_supported=['S256'],
                   scopes_supported=SCOPES, authorization_response_iss_parameter_supported=True,
                   client_id_metadata_document_supported=False)


@routes.post('/oauth/register')
def register():
    if request.content_length is None or request.content_length > 8192:
        raise OAuthError('invalid_client_metadata', '클라이언트 설정이 너무 큽니다.')
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise OAuthError('invalid_client_metadata', 'JSON 클라이언트 설정이 필요합니다.')
    urls = body.get('redirect_uris')
    if not isinstance(urls, list) or not 1 <= len(urls) <= 4 or not all(allowed_redirect(u) for u in urls):
        raise OAuthError('invalid_redirect_uri', 'ChatGPT 공식 콜백 또는 Codex 로컬 콜백 주소만 등록할 수 있습니다.')
    if body.get('token_endpoint_auth_method', 'none') != 'none':
        raise OAuthError('invalid_client_metadata', 'S256 PKCE를 사용하는 공개 클라이언트만 지원합니다.')
    grants = body.get('grant_types', ['authorization_code', 'refresh_token'])
    if (not isinstance(grants, list) or not all(isinstance(g, str) for g in grants)
            or set(grants) - {'authorization_code', 'refresh_token'}):
        raise OAuthError('invalid_client_metadata', '지원하지 않는 인증 방식입니다.')
    scopes = body.get('scope', ' '.join(SCOPES))
    if not isinstance(scopes, str) or not scopes.split() or set(scopes.split()) - set(SCOPES):
        raise OAuthError('invalid_scope', '독서 조회와 비공개 초안 저장 권한만 지원합니다.')
    data = {'v': 1, 'redirect_uris': urls, 'scope': scopes.split(), 'nonce': secrets.token_hex(8)}
    return jsonify(client_id=client_signer().dumps(data), client_id_issued_at=int(time.time()),
                   redirect_uris=urls, token_endpoint_auth_method='none',
                   grant_types=['authorization_code', 'refresh_token'], response_types=['code'], scope=scopes), 201


def authorization_request():
    values = request.args
    client_id = values.get('client_id', '')
    client = client_metadata(client_id)
    redirect_uri = values.get('redirect_uri', '')
    if not redirect_matches(redirect_uri, client['redirect_uris']):
        raise OAuthError('invalid_request', '등록한 콜백 주소와 일치하지 않습니다.')
    if values.get('response_type') != 'code' or values.get('code_challenge_method') != 'S256':
        raise OAuthError('invalid_request', 'authorization code와 S256 PKCE가 필요합니다.')
    if not re.fullmatch(r'[A-Za-z0-9_-]{43}', values.get('code_challenge', '')):
        raise OAuthError('invalid_request', 'PKCE challenge 형식이 맞지 않습니다.')
    if values.get('resource') != resource():
        raise OAuthError('invalid_target', 'Railway /mcp 주소에 대한 연결만 승인할 수 있습니다.')
    scopes = values.get('scope', ' '.join(client['scope'])).split()
    if not scopes or set(scopes) - set(client['scope']) or set(scopes) - set(SCOPES):
        raise OAuthError('invalid_scope', '요청한 권한을 확인해 주세요.')
    state = values.get('state', '')
    if len(state) > 2048:
        raise OAuthError('invalid_request', 'state가 너무 깁니다.')
    return {'client_id': client_id, 'redirect_uri': redirect_uri, 'challenge': values['code_challenge'],
            'resource': resource(), 'scope': scopes, 'state': state}


def authorize():
    """Registered under admin_required and CSRF protection in admin.py."""
    try:
        grant = authorization_request()
    except OAuthError as error:
        return oauth_error(error)
    if request.method == 'GET':
        return render_template('admin/mcp_authorize.html', scopes=grant['scope'], mcp_url=resource())
    params = {'state': grant['state'], 'iss': origin()}
    if request.form.get('decision') != 'approve':
        params['error'] = 'access_denied'
    else:
        profile, state = locked_state()
        if len(state['codes']) >= 16 or len(state['grants']) >= 32:
            raise OAuthError('temporarily_unavailable', '기존 연결을 해제한 뒤 다시 승인해 주세요.', 429)
        code = secrets.token_urlsafe(32)
        state['codes'][sha(code)] = {**grant, 'expires': time.time() + CODE_TTL, 'owner': owner_fingerprint()}
        save_state(profile, state)
        params['code'] = code
    return redirect(grant['redirect_uri'] + ('&' if '?' in grant['redirect_uri'] else '?') + urlencode(params), code=303)


def issue_tokens(state, grant):
    access = 'hy_mcp_a_' + secrets.token_urlsafe(32)
    family = grant.get('family') or secrets.token_hex(16)
    refresh = 'hy_mcp_r_' + refresh_signer().dumps({'family': family, 'nonce': secrets.token_urlsafe(32),
                                                  'client': sha(grant['client_id']), 'resource': grant['resource']})
    now = time.time()
    state['grants'][sha(access)] = {'refresh_hash': sha(refresh), 'access_expires': now + ACCESS_TTL,
                                  'refresh_expires': now + REFRESH_TTL, 'scope': grant['scope'],
                                  'client_id': grant['client_id'], 'resource': grant['resource'],
                                  'owner': grant['owner'], 'family': family}
    return {'access_token': access, 'refresh_token': refresh, 'token_type': 'Bearer',
            'expires_in': ACCESS_TTL, 'scope': ' '.join(grant['scope'])}


@routes.post('/oauth/token')
def token():
    if request.content_length is None or request.content_length > 16_384:
        raise OAuthError('invalid_request', '토큰 요청 크기를 확인해 주세요.')
    values = request.form
    client_id = values.get('client_id', '')
    client_metadata(client_id)
    if values.get('resource') != resource():
        raise OAuthError('invalid_target', '토큰의 대상 주소가 일치하지 않습니다.')
    profile, state = locked_state()
    if values.get('grant_type') == 'authorization_code':
        key = sha(values.get('code', ''))
        grant = state['codes'].get(key)
        verifier = values.get('code_verifier', '')
        valid_verifier = re.fullmatch(r'[A-Za-z0-9._~-]{43,128}', verifier)
        computed = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode() if valid_verifier else ''
        if (not grant or grant['client_id'] != client_id or grant['owner'] != owner_fingerprint()
                or grant['redirect_uri'] != values.get('redirect_uri') or grant['resource'] != resource()
                or not computed or not hmac.compare_digest(grant['challenge'], computed)):
            raise OAuthError('invalid_grant', '인증 코드 또는 PKCE 확인에 실패했습니다.')
        del state['codes'][key]
    elif values.get('grant_type') == 'refresh_token':
        raw_refresh = values.get('refresh_token', '')
        try:
            if not raw_refresh.startswith('hy_mcp_r_'):
                raise BadSignature('Invalid prefix')
            payload = refresh_signer().loads(raw_refresh[len('hy_mcp_r_'):], max_age=REFRESH_TTL)
        except BadSignature:
            raise OAuthError('invalid_grant', '갱신 토큰이 유효하지 않습니다.') from None
        refresh_hash = sha(raw_refresh)
        found = next(((k, g) for k, g in state['grants'].items()
                      if g['family'] == payload.get('family')), None)
        if not found:
            raise OAuthError('invalid_grant', '연결을 다시 승인해 주세요.')
        key, grant = found
        if (grant['client_id'] != client_id or payload.get('client') != sha(client_id)
                or grant['resource'] != resource() or payload.get('resource') != resource()
                or grant['owner'] != owner_fingerprint()):
            raise OAuthError('invalid_grant', '이 클라이언트의 갱신 토큰이 아닙니다.')
        if not hmac.compare_digest(grant['refresh_hash'], refresh_hash):
            # A valid, previously issued refresh token was replayed: revoke its
            # whole family across workers, without retaining old bearer tokens.
            del state['grants'][key]
            save_state(profile, state)
            raise OAuthError('invalid_grant', '갱신 토큰 재사용이 감지되어 연결을 해제했습니다. 다시 승인해 주세요.')
        requested_scope = values.get('scope')
        if requested_scope is not None:
            requested = requested_scope.split()
            if not requested or set(requested) - set(grant['scope']):
                raise OAuthError('invalid_scope', '토큰 권한을 확대할 수 없습니다.')
            grant = {**grant, 'scope': requested}
        del state['grants'][key]
    else:
        raise OAuthError('unsupported_grant_type', '지원하지 않는 인증 방식입니다.')
    result = issue_tokens(state, grant)
    save_state(profile, state)
    return jsonify(result)


@routes.post('/oauth/revoke')
def revoke():
    if request.content_length is None or request.content_length > 16_384:
        raise OAuthError('invalid_request', '요청 크기를 확인해 주세요.')
    client_id = request.form.get('client_id', '')
    client_metadata(client_id)
    target = sha(request.form.get('token', ''))
    profile, state = locked_state()
    state['grants'] = {k: g for k, g in state['grants'].items()
                       if not (g['client_id'] == client_id and (hmac.compare_digest(k, target) or hmac.compare_digest(g['refresh_hash'], target)))}
    save_state(profile, state)
    return '', 200


def authenticate(required_scope):
    header = request.headers.get('Authorization', '')
    value = header[7:] if header.startswith('Bearer ') else ''
    if not value.startswith('hy_mcp_a_') or len(value) > 256:
        return None
    state = stored_state(Profile.query.order_by(Profile.id).first())
    grant = state.get('grants', {}).get(sha(value))
    if (not grant or grant['access_expires'] <= time.time() or grant['resource'] != resource()
            or grant['owner'] != owner_fingerprint()):
        return None
    if required_scope not in grant['scope']:
        raise OAuthError('insufficient_scope', '이 도구에 필요한 권한을 다시 승인해 주세요.', 403)
    return grant


def revoke_all():
    profile, state = locked_state()
    save_state(profile, {'codes': {}, 'grants': {}})
    return redirect(url_for('admin.chatgpt'), code=303)


def connection_count():
    state = stored_state(Profile.query.order_by(Profile.id).first())
    return sum(g['refresh_expires'] > time.time() for g in state.get('grants', {}).values())
