"""Owner login → HTTPS consent → OAuth token → direct MCP round trip.
Only uses a temporary database with explicitly synthetic reading notes.
"""
import asyncio
import base64
import hashlib
import os
import sys
import tempfile
import threading
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit

root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
tmp=tempfile.TemporaryDirectory(prefix='hy-mcp-https-')
os.environ.update(ENV_FILE=str(Path(tmp.name)/'unused-env'),DATABASE_URL='sqlite:///'+str(Path(tmp.name)/'test.db'),
                  SECRET_KEY='mcp-https-fixture-only',NOTION_TOKEN='',SUPABASE_URL='',SUPABASE_SERVICE_KEY='')
from app import app
from models import db,Profile,Book,Archive
from werkzeug.security import generate_password_hash
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright
app.config.update(TESTING=True,ADMIN_USERNAME='fixture-owner',ADMIN_PASSWORD_HASH=generate_password_hash('fixture-pass'),SESSION_COOKIE_SECURE=True)
with app.app_context():
    db.create_all();db.session.add(Profile(name='HTTPS 검증',headline='검증'))
    book=Book(title='총, 균, 쇠',summary='실제 독서 내용이 아닌 연결 검증용 메모');db.session.add(book);db.session.commit();book_id=book.id
server=make_server('127.0.0.1',0,app,threaded=True,ssl_context='adhoc')
base=f'https://127.0.0.1:{server.server_port}';app.config['SITE_URL']=base
threading.Thread(target=server.serve_forever,daemon=True).start()
verifier='a'*64;challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
callback='https://chatgpt.com/connector_platform_oauth_redirect';received={}
try:
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless=True)
        ctx=browser.new_context(ignore_https_errors=True)
        def requests(route):
            parsed=urlsplit(route.request.url)
            if parsed.hostname=='127.0.0.1':
                if parsed.path=='/admin/mcp/authorize' and route.request.method=='POST':
                    response=route.fetch(max_redirects=0)
                    assert response.status==303,response.status
                    destination=response.headers['location']
                    assert destination.startswith(callback)
                    received.update(parse_qs(urlsplit(destination).query))
                    route.fulfill(status=200,content_type='text/html; charset=utf-8',body='<h1>승인 콜백 수신</h1>')
                else:route.continue_()
            else:route.abort()
        ctx.route('**/*',requests)
        client=ctx.request.post(base+'/oauth/register',data={'redirect_uris':[callback],'token_endpoint_auth_method':'none'}).json()
        client_id=client['client_id']
        args={'response_type':'code','client_id':client_id,'redirect_uri':callback,'resource':base+'/mcp',
              'scope':'reading:read drafts:write','code_challenge':challenge,'code_challenge_method':'S256','state':'fixture-state'}
        page=ctx.new_page();page.goto(base+'/admin/mcp/authorize?'+urlencode(args))
        page.locator('#username').fill('fixture-owner');page.locator('#password').fill('fixture-pass')
        page.locator('.login-form button').click();page.get_by_role('button',name='연결 승인').wait_for()
        page.get_by_role('button',name='연결 승인').click();page.get_by_role('heading',name='승인 콜백 수신').wait_for()
        assert received['state']==['fixture-state'];assert received['iss']==[base]
        response=ctx.request.post(base+'/oauth/token',form={'client_id':client_id,'grant_type':'authorization_code','resource':base+'/mcp',
            'code':received['code'][0],'code_verifier':verifier,'redirect_uri':callback})
        assert response.status==200,response.status
        access=response.json()['access_token']
        # A raw MCP client transport must work without browser cookies.
        async def verify_sdk():
            import httpx2 as httpx
            from mcp import ClientSession
            from mcp.client.streamable_http import streamable_http_client
            async with httpx.AsyncClient(verify=False,headers={'Authorization':'Bearer '+access},timeout=20) as http:
                async with streamable_http_client(base+'/mcp',http_client=http) as streams:
                    async with ClientSession(streams[0],streams[1]) as session:
                        await session.initialize()
                        listed=await session.list_tools();assert len(listed.tools)==5
                        found=await session.call_tool('listReadingBooks',{'q':'총, 균, 쇠'})
                        assert found.structured_content['books'][0]['id']==book_id
                        source=await session.call_tool('getReadingSource',{'book_id':book_id})
                        before=await session.call_tool('getReadingDraft',{'book_id':book_id});assert not before.structured_content['exists']
                        payload={'book_id':book_id,'source_token':source.structured_content['source_token'],'title':'MCP 연결 검증용 초안',
                                 'blocks':[{'type':'paragraph','text':'임시 DB에만 저장하는 검증용 초안입니다.'}]}
                        saved=await session.call_tool('saveReadingDraft',payload);assert not saved.is_error
                        assert saved.structured_content['status']=='draft'
                        second=await session.call_tool('saveReadingDraft',payload)
                        assert second.structured_content['id']==saved.structured_content['id']
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(lambda: asyncio.run(verify_sdk())).result(timeout=60)
        with app.app_context():assert Archive.query.count()==1;assert Archive.query.first().status=='draft'
        # Read the management page after real authorization; revoke via the actual CSRF-protected form.
        page.goto(base+'/admin/chatgpt');page.get_by_role('button',name='MCP 연결 모두 해제').click()
        page.get_by_role('button',name='한 번 더 누르면 삭제돼요').click()
        page.wait_for_url(base+'/admin/chatgpt')
        assert ctx.request.post(base+'/mcp',data={'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'listReadingBooks','arguments':{}}},
                                headers={'Authorization':'Bearer '+access}).status==401
        browser.close()
    print('PASS: real HTTPS login/consent, PKCE token, official MCP SDK initialization and five tools, fixture book→source→draft round trip, idempotent save, owner revocation.')
finally:
    server.shutdown();tmp.cleanup()
