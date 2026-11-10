"""OAuth/MCP regression checks with isolated SQLite and no external requests."""
import base64
import copy
import hashlib
import re
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit

from flask import Blueprint, Flask
from flask_wtf.csrf import CSRFProtect

import chatgpt_bridge as reading
import mcp_auth as oauth
import mcp_server as server
from auth import admin_required, is_admin
from models import Archive, Book, Profile, db


class MCPConnectionTests(unittest.TestCase):
    def setUp(self):
        self.app=Flask(__name__,root_path=str(Path(__file__).resolve().parents[1]))
        self.app.config.update(TESTING=True,SECRET_KEY='mcp-isolated-test',SQLALCHEMY_DATABASE_URI='sqlite://',
                               SQLALCHEMY_TRACK_MODIFICATIONS=False,SITE_URL='https://portfolio.example',NOTION_TOKEN='',
                               ADMIN_USERNAME='owner',ADMIN_PASSWORD_HASH='test-hash')
        db.init_app(self.app);csrf=CSRFProtect(self.app)
        for blueprint in (oauth.routes,server.routes,reading.api):
            csrf.exempt(blueprint);self.app.register_blueprint(blueprint)
        admin=Blueprint('admin',__name__,url_prefix='/admin')
        @admin.route('/mcp/authorize',methods=['GET','POST'])
        @admin_required
        def mcp_authorize():return oauth.authorize()
        @admin.post('/mcp/revoke')
        @admin_required
        def mcp_revoke():return oauth.revoke_all()
        for endpoint,path in [('dashboard','/'),('login','/login'),('write','/write'),('chatgpt','/chatgpt'),
                              ('importer','/import'),('showcases','/showcases'),('comments','/comments'),('logout','/logout')]:
            admin.add_url_rule(path,endpoint,lambda:'OK')
        self.app.register_blueprint(admin);self.app.add_url_rule('/','home',lambda:'home')
        self.app.jinja_env.filters.update(date=lambda x,*a:str(x),excerpt=lambda x,*a:str(x),minutes=lambda x:1,nl=lambda x:x)
        @self.app.context_processor
        def context():return {'is_admin':is_admin(),'profile':Profile.query.first()}
        self.ctx=self.app.app_context();self.ctx.push();db.create_all()
        db.session.add(Profile(name='소유자',headline='검증',extra={'keep':'untouched'}))
        self.book=Book(title='총, 균, 쇠',author='재레드 다이아몬드',summary='검증용 원문 메모')
        db.session.add(self.book);db.session.commit();self.book_id=self.book.id
        self.client=self.app.test_client()
        self.redirect='https://chatgpt.com/connector_platform_oauth_redirect'
        self.resource='https://portfolio.example/mcp';self.verifier='v'*43
        self.challenge=base64.urlsafe_b64encode(hashlib.sha256(self.verifier.encode()).digest()).rstrip(b'=').decode()
        self.client_id=self.register()

    def tearDown(self):
        db.session.remove();db.drop_all();self.ctx.pop()

    def register(self,scope='reading:read drafts:write'):
        r=self.client.post('/oauth/register',json={'redirect_uris':[self.redirect],'token_endpoint_auth_method':'none','scope':scope})
        self.assertEqual(r.status_code,201,r.json);return r.json['client_id']

    def authorization_url(self,**overrides):
        args={'response_type':'code','client_id':self.client_id,'redirect_uri':self.redirect,'resource':self.resource,
              'code_challenge':self.challenge,'code_challenge_method':'S256','state':'original-state','scope':'reading:read drafts:write'}
        args.update(overrides);return '/admin/mcp/authorize?'+urlencode(args)

    def consent(self,scope='reading:read drafts:write',decision='approve'):
        with self.client.session_transaction() as s:s['admin']=True
        url=self.authorization_url(scope=scope)
        response=self.client.get(url);self.assertEqual(response.status_code,200,response.text)
        csrf=re.search(r'name="csrf_token" value="([^"]+)"',response.text).group(1)
        r=self.client.post(url,data={'csrf_token':csrf,'decision':decision})
        self.assertEqual(r.status_code,303,r.text)
        values=parse_qs(urlsplit(r.location).query)
        self.assertEqual(values['state'],['original-state']);self.assertEqual(values['iss'],['https://portfolio.example'])
        return values

    def exchange(self,code,**overrides):
        data={'grant_type':'authorization_code','client_id':self.client_id,'redirect_uri':self.redirect,
              'resource':self.resource,'code':code,'code_verifier':self.verifier}
        data.update(overrides);return self.client.post('/oauth/token',data=data)

    def tokens(self,scope='reading:read drafts:write'):
        code=self.consent(scope)['code'][0];r=self.exchange(code)
        self.assertEqual(r.status_code,200,r.json);return r.json

    def rpc(self,method,params=None,token=None,**kwargs):
        headers={'MCP-Protocol-Version':'2025-06-18',**kwargs.pop('headers',{})}
        if token:headers['Authorization']='Bearer '+token
        return self.client.post('/mcp',json={'jsonrpc':'2.0','id':1,'method':method,'params':params or {}},headers=headers,**kwargs)

    def call(self,name,args=None,token=None):
        return self.rpc('tools/call',{'name':name,'arguments':args or {}},token)

    def test_metadata_resource_pkce_and_discovery(self):
        r=self.client.get('/.well-known/oauth-protected-resource/mcp')
        self.assertEqual(r.json['resource'],self.resource)
        self.assertEqual(r.headers['Cache-Control'],'no-store')
        meta=self.client.get('/.well-known/oauth-authorization-server').json
        self.assertEqual(meta['code_challenge_methods_supported'],['S256'])
        self.assertEqual(meta['token_endpoint_auth_methods_supported'],['none'])
        self.assertTrue(meta['authorization_response_iss_parameter_supported'])
        self.assertEqual(self.rpc('server/discover').json['result']['supportedVersions'][0],'2026-07-28')
        self.assertEqual(self.rpc('initialize',{'protocolVersion':'2025-06-18'}).json['result']['protocolVersion'],'2025-06-18')

    def test_registration_rejects_unsafe_callbacks_and_unknown_scopes(self):
        for redirect in ['https://evil.example/callback','http://chatgpt.com/connector_platform_oauth_redirect',
                         'https://chatgpt.com.evil.example/connector_platform_oauth_redirect','https://chatgpt.com@evil.example/callback']:
            self.assertEqual(self.client.post('/oauth/register',json={'redirect_uris':[redirect]}).status_code,400)
        self.assertEqual(self.client.post('/oauth/register',json={'redirect_uris':[self.redirect],'scope':'publish delete'}).status_code,400)
        self.assertEqual(self.client.post('/oauth/register',json={'redirect_uris':[self.redirect],'token_endpoint_auth_method':'client_secret_post'}).status_code,400)

    def test_codex_loopback_callback_and_pkce_with_dynamic_port(self):
        self.redirect='http://127.0.0.1/callback'
        self.client_id=self.register()
        self.redirect='http://127.0.0.1:51891/callback'
        token=self.tokens()['access_token']
        self.assertEqual(self.call('listReadingBooks',token=token).status_code,200)
        self.assertFalse(oauth.redirect_matches('http://127.0.0.1:51891/callback/other', ['http://127.0.0.1/callback']))
        for invalid in ['http://localhost/callback','http://127.0.0.1.evil.example/callback',
                        'http://127.0.0.1@evil.example/callback','http://127.0.0.1/callback?next=https://evil.example',
                        'http://127.0.0.1/admin','http://192.168.1.2/callback','http://127.0.0.1:99999/callback']:
            self.assertFalse(oauth.allowed_redirect(invalid),invalid)

    def test_authorization_requires_owner_login_and_csrf(self):
        r=self.client.get(self.authorization_url());self.assertEqual(r.status_code,303);self.assertIn('/admin/login',r.location)
        with self.client.session_transaction() as s:s['admin']=True
        self.assertEqual(self.client.post(self.authorization_url(),data={'decision':'approve'}).status_code,400)
        self.assertEqual(oauth.stored_state(Profile.query.first())['codes'],{})

    def test_authorization_validates_resource_callback_and_pkce(self):
        with self.client.session_transaction() as s:s['admin']=True
        for overrides in [{'resource':'https://evil.example/mcp'},{'redirect_uri':'https://evil.example/cb'},
                          {'code_challenge_method':'plain'},{'code_challenge':'invalid'}]:
            r=self.client.get(self.authorization_url(**overrides));self.assertEqual(r.status_code,400,r.text)

    def test_denied_consent_does_not_issue_code(self):
        values=self.consent(decision='deny');self.assertEqual(values['error'],['access_denied'])
        self.assertNotIn('code',values)

    def test_token_exchange_checks_pkce_and_code_is_single_use(self):
        code=self.consent()['code'][0]
        self.assertEqual(self.exchange(code,code_verifier='w'*43).status_code,400)
        r=self.exchange(code);self.assertEqual(r.status_code,200,r.json)
        self.assertEqual(self.exchange(code).status_code,400)
        text=str(Profile.query.first().extra)
        self.assertNotIn(r.json['access_token'],text);self.assertNotIn(r.json['refresh_token'],text)
        self.assertNotIn(code,text);self.assertEqual(Profile.query.first().extra['keep'],'untouched')

    def test_code_bound_to_client_redirect_resource_and_owner(self):
        code=self.consent()['code'][0];other=self.register()
        for overrides in [{'client_id':other},{'redirect_uri':'https://chatgpt.com/connector/oauth/other'},
                          {'resource':'https://other.example/mcp'}]:
            self.assertEqual(self.exchange(code,**overrides).status_code,400)
        self.app.config['ADMIN_PASSWORD_HASH']='new-owner-credential'
        self.assertEqual(self.exchange(code).status_code,400)

    def test_expired_code_is_rejected(self):
        code=self.consent()['code'][0];p=Profile.query.first();state=oauth.stored_state(p)
        state['codes'][oauth.sha(code)]['expires']=0;oauth.save_state(p,state)
        self.assertEqual(self.exchange(code).status_code,400)

    def test_anonymous_cookie_and_legacy_api_key_cannot_read(self):
        for token in [None,'hy_legacy-key']:
            r=self.call('listReadingBooks',token=token);self.assertEqual(r.status_code,401)
            self.assertIn('resource_metadata=',r.headers['WWW-Authenticate'])
            self.assertIn('mcp/www_authenticate',r.json['result']['_meta'])
            challenge=r.json['result']['_meta']['mcp/www_authenticate'][0]
            self.assertIn('error="invalid_token"',challenge)
            self.assertIn('error_description=',challenge)
            self.assertEqual(challenge,r.headers['WWW-Authenticate'])
        with self.client.session_transaction() as s:s['admin']=True
        self.assertEqual(self.call('listReadingBooks').status_code,401)

    def test_tools_describe_only_scoped_reading_and_private_draft_operations(self):
        tools=self.rpc('tools/list').json['result']['tools']
        self.assertEqual({t['name'] for t in tools},set(server.TOOL_SCOPES))
        self.assertFalse(any('publish' in t['name'].lower() or 'delete' in t['name'].lower() for t in tools))
        self.assertTrue(all(t['securitySchemes'][0]['type']=='oauth2' for t in tools))
        self.assertTrue(all(t['_meta']['securitySchemes']==t['securitySchemes'] for t in tools))

    def test_full_workflow_book_source_existing_draft_save_without_proxy(self):
        token=self.tokens()['access_token']
        listed=self.call('listReadingBooks',{'q':'총, 균, 쇠'},token).json['result']['structuredContent']
        self.assertEqual(listed['books'][0]['id'],self.book_id)
        source=self.call('getReadingSource',{'book_id':self.book_id},token).json['result']['structuredContent']
        before=self.call('getReadingDraft',{'book_id':self.book_id},token).json['result']['structuredContent']
        self.assertFalse(before['exists'])
        args={'book_id':self.book_id,'source_token':source['source_token'],'title':'총, 균, 쇠 — 독서 메모',
              'blocks':[{'type':'heading','text':'핵심'}, {'type':'paragraph','text':'검증용 원문에 기반한 요약'}]}
        saved=self.call('saveReadingDraft',args,token).json['result']
        self.assertFalse(saved['isError']);self.assertEqual(saved['structuredContent']['status'],'draft')
        second=self.call('saveReadingDraft',args,token).json['result']['structuredContent']
        self.assertEqual(saved['structuredContent']['id'],second['id']);self.assertEqual(Archive.query.count(),1)
        self.assertEqual(Archive.query.first().status,'draft')

    def test_read_only_token_cannot_write_and_scope_cannot_be_expanded(self):
        self.client_id=self.register('reading:read')
        tokens=self.tokens('reading:read')
        self.assertEqual(self.call('saveReadingDraft',{'book_id':self.book_id},tokens['access_token']).status_code,403)
        r=self.client.post('/oauth/token',data={'grant_type':'refresh_token','client_id':self.client_id,'resource':self.resource,
                                               'refresh_token':tokens['refresh_token'],'scope':'reading:read drafts:write'})
        self.assertEqual(r.status_code,400);self.assertEqual(Archive.query.count(),0)

    def test_refresh_rotates_tokens_and_previous_tokens_stop_working(self):
        old=self.tokens()
        data={'grant_type':'refresh_token','client_id':self.client_id,'resource':self.resource,'refresh_token':old['refresh_token']}
        r=self.client.post('/oauth/token',data=data);self.assertEqual(r.status_code,200,r.json)
        self.assertEqual(self.call('listReadingBooks',token=r.json['access_token']).status_code,200)
        self.assertEqual(self.client.post('/oauth/token',data=data).status_code,400)
        self.assertEqual(self.call('listReadingBooks',token=old['access_token']).status_code,401)
        self.assertEqual(self.call('listReadingBooks',token=r.json['access_token']).status_code,401)

    def test_access_expiration_revocation_and_owner_rotation(self):
        tokens=self.tokens();p=Profile.query.first();state=oauth.stored_state(p)
        state['grants'][oauth.sha(tokens['access_token'])]['access_expires']=0;oauth.save_state(p,state)
        self.assertEqual(self.call('listReadingBooks',token=tokens['access_token']).status_code,401)
        active=self.tokens()
        self.assertEqual(self.client.post('/oauth/revoke',data={'client_id':self.client_id,'token':active['refresh_token']}).status_code,200)
        self.assertEqual(self.call('listReadingBooks',token=active['access_token']).status_code,401)
        active=self.tokens();self.app.config['ADMIN_PASSWORD_HASH']='changed'
        self.assertEqual(self.call('listReadingBooks',token=active['access_token']).status_code,401)

    def test_unknown_tool_invalid_arguments_and_malicious_origin(self):
        token=self.tokens()['access_token']
        self.assertIn('error',self.call('publishPost',{},token).json)
        self.assertTrue(self.call('getReadingSource',{'book_id':True},token).json['result']['isError'])
        self.assertTrue(self.call('listReadingBooks',{'unknown':'value'},token).json['result']['isError'])
        self.assertEqual(self.rpc('tools/list',headers={'Origin':'https://evil.example'}).status_code,403)
        self.assertEqual(self.client.get('/mcp').status_code,405)
        self.assertEqual(self.client.post('/mcp',json=[]).status_code,400)


if __name__=='__main__':unittest.main()
