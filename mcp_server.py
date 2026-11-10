"""Stateless JSON-RPC MCP transport in the existing Flask/Gunicorn service.

Every private tool verifies OAuth before calling shared reading functions. No
Sites proxy, loopback HTTP request, browser session, or legacy API key is used.
"""
import copy
import json
from urllib.parse import urlsplit

from flask import Blueprint, current_app, jsonify, request

import chatgpt_bridge as reading
import mcp_auth as oauth
from models import db

routes = Blueprint('reading_mcp', __name__)
VERSIONS = ['2026-07-28', '2025-11-25', '2025-06-18', '2024-11-05']
TOOL_SCOPES = {'listReadingBooks': 'reading:read', 'listReadingPages': 'reading:read',
               'getReadingSource': 'reading:read', 'getReadingDraft': 'reading:read',
               'saveReadingDraft': 'drafts:write'}


def tools():
    from chatgpt_schema import build_schema
    definitions = []
    for path, methods in build_schema(oauth.origin())['paths'].items():
        for method, operation in methods.items():
            name = operation['operationId']
            schema = {'type': 'object', 'properties': {}, 'additionalProperties': False, 'required': []}
            for parameter in operation.get('parameters', []):
                prop = copy.deepcopy(parameter['schema'])
                prop['description'] = parameter.get('description', parameter['name'])
                if parameter['name'] == 'book_id':
                    prop['minimum'] = 1
                schema['properties'][parameter['name']] = prop
                if parameter.get('required'):
                    schema['required'].append(parameter['name'])
            if method == 'put':
                body = copy.deepcopy(operation['requestBody']['content']['application/json']['schema'])
                schema['properties'].update(body['properties'])
                schema['required'].extend(body['required'])
            scope = TOOL_SCOPES[name]
            definitions.append({'name': name, 'title': operation['summary'], 'description': operation['description'],
                                'inputSchema': schema, 'securitySchemes': [{'type': 'oauth2', 'scopes': [scope]}],
                                '_meta': {'securitySchemes': [{'type': 'oauth2', 'scopes': [scope]}]},
                                'annotations': {'readOnlyHint': method == 'get', 'destructiveHint': False,
                                                'idempotentHint': True, 'openWorldHint': False}})
    return definitions


def validate_arguments(name, args):
    if not isinstance(args, dict):
        raise reading.BridgeError('도구 입력은 JSON 객체여야 합니다.')
    definition = next(t for t in tools() if t['name'] == name)['inputSchema']
    if set(args) - set(definition['properties']) or set(definition['required']) - set(args):
        raise reading.BridgeError('필수 입력 또는 지원하는 필드를 확인해 주세요.')
    for field in ('book_id', 'offset'):
        if field in args and (type(args[field]) is not int or args[field] < (1 if field == 'book_id' else 0)):
            raise reading.BridgeError('책 ID와 offset은 올바른 정수여야 합니다.')
    for field in ('q', 'page_id', 'source_token', 'title', 'summary', 'expected_revision', 'cover_asset_id'):
        if field in args and not isinstance(args[field], str):
            raise reading.BridgeError(f'{field}는 문자열이어야 합니다.')


def call_tool(name, args):
    validate_arguments(name, args)
    if name == 'listReadingBooks':
        return reading.list_reading_books(args.get('q', ''), args.get('offset', 0))
    if name == 'listReadingPages':
        return reading.list_reading_pages(args['book_id'])
    if name == 'getReadingSource':
        return reading.source_data(reading.book_or_error(args['book_id']), args.get('page_id'))
    if name == 'getReadingDraft':
        return reading.get_reading_draft(args['book_id'], args.get('page_id'))
    return reading.save_reading_draft(args['book_id'], {k: v for k, v in args.items() if k != 'book_id'})


def rpc_error(identifier, code, message, status=200):
    return jsonify(jsonrpc='2.0', id=identifier, error={'code': code, 'message': message}), status


def rpc_result(identifier, result):
    return jsonify(jsonrpc='2.0', id=identifier, result=result)


def tool_error(identifier, message, status=200, auth=False, auth_error='invalid_token'):
    value = {'content': [{'type': 'text', 'text': message}], 'isError': True}
    if auth:
        value['_meta'] = {'mcp/www_authenticate': [oauth.challenge(auth_error)]}
    response = jsonify(jsonrpc='2.0', id=identifier, result=value)
    response.status_code = status
    if auth:
        response.headers['WWW-Authenticate'] = oauth.challenge(auth_error)
    return response


@routes.after_request
def response_headers(response):
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


@routes.route('/mcp', methods=['POST', 'GET', 'DELETE'])
def mcp():
    if request.method != 'POST':
        response = jsonify(error='This stateless MCP server accepts POST JSON-RPC requests.')
        response.status_code = 405
        response.headers['Allow'] = 'POST'
        return response
    if request.headers.get('Origin') and request.headers['Origin'].rstrip('/') not in (oauth.origin(), 'https://chatgpt.com', 'https://chat.openai.com'):
        return jsonify(error='Untrusted Origin'), 403
    if request.content_length is None or request.content_length > reading.MAX_BODY:
        return jsonify(error='Invalid request size'), 413
    version = request.headers.get('MCP-Protocol-Version')
    if version and version not in VERSIONS:
        return jsonify(error='Unsupported MCP protocol version'), 400
    message = request.get_json(silent=True)
    if not isinstance(message, dict) or message.get('jsonrpc') != '2.0':
        return rpc_error(None, -32600, 'Invalid JSON-RPC request', 400)
    identifier = message.get('id')
    if identifier is not None and (type(identifier) not in (int, str)):
        return rpc_error(None, -32600, 'Invalid request ID', 400)
    method, params = message.get('method'), message.get('params', {})
    if not isinstance(params, dict):
        return rpc_error(identifier, -32602, 'Invalid params')
    if method in ('notifications/initialized', 'notifications/cancelled'):
        return '', 202
    if 'id' not in message:
        return rpc_error(None, -32600, 'A request ID is required', 400)
    if method == 'server/discover':
        return rpc_result(identifier, {'supportedVersions': VERSIONS, 'capabilities': {'tools': {}},
                                       'serverInfo': {'name': 'HY ARCHIVE Reading', 'version': '1.0.0'}})
    if method == 'initialize':
        requested = params.get('protocolVersion')
        return rpc_result(identifier, {'protocolVersion': requested if requested in VERSIONS else VERSIONS[0],
                                       'capabilities': {'tools': {'listChanged': False}},
                                       'serverInfo': {'name': 'HY ARCHIVE Reading', 'version': '1.0.0'},
                                       'instructions': '관리자 로그인 후 권한을 승인해 주세요. 독서 기록 조회와 비공개 초안 저장만 가능합니다. 발행·삭제는 홈페이지에서 직접 합니다.'})
    if method == 'ping':
        return rpc_result(identifier, {})
    if method == 'tools/list':
        return rpc_result(identifier, {'tools': tools()})
    if method != 'tools/call':
        return rpc_error(identifier, -32601, 'Method not found')
    name = params.get('name')
    if not isinstance(name, str) or name not in TOOL_SCOPES:
        return rpc_error(identifier, -32602, 'Unknown tool')
    try:
        if oauth.authenticate(TOOL_SCOPES[name]) is None:
            return tool_error(identifier, '홈페이지 관리자 계정으로 로그인하여 ChatGPT 연결을 승인해 주세요.', 401, auth=True)
        result = call_tool(name, params.get('arguments', {}))
        return rpc_result(identifier, {'content': [{'type': 'text', 'text': json.dumps(result, ensure_ascii=False)}],
                                       'structuredContent': result, 'isError': False})
    except oauth.OAuthError as error:
        db.session.rollback()
        return tool_error(identifier, error.description, error.status, auth=True, auth_error=error.error)
    except reading.BridgeError as error:
        db.session.rollback()
        return tool_error(identifier, str(error))
    except Exception:
        db.session.rollback()
        current_app.logger.exception('MCP tool failed: %s', name)
        return tool_error(identifier, '처리하지 못했습니다. 저장 여부는 기존 초안 조회로 먼저 확인해 주세요.')
