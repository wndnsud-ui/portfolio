"""HTTPS browser regression for key issuance; never uses production data/keys."""
import os
import sys
import tempfile
import threading
from pathlib import Path
from urllib.parse import urlsplit

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
tmp=tempfile.TemporaryDirectory(prefix='hy-key-https-')
os.environ.update(ENV_FILE=str(Path(tmp.name)/'no-env'),DATABASE_URL='sqlite:///'+str(Path(tmp.name)/'test.db'),
                  SECRET_KEY='isolated-https-test-only',NOTION_TOKEN='',SUPABASE_URL='',SUPABASE_SERVICE_KEY='')
from app import app
from models import db,Profile
from chatgpt_bridge import digest,key_info
from werkzeug.security import generate_password_hash
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright
app.config.update(TESTING=True,SESSION_COOKIE_SECURE=True,ADMIN_USERNAME='test-user',ADMIN_PASSWORD_HASH=generate_password_hash('test-pass'))
with app.app_context():
    db.create_all();db.session.add(Profile(name='HTTPS 테스트',headline='검증'));db.session.commit()
server=make_server('127.0.0.1',0,app,threaded=True,ssl_context='adhoc')
threading.Thread(target=server.serve_forever,daemon=True).start()
base=f'https://127.0.0.1:{server.server_port}'
try:
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless=True)
        ctx=browser.new_context(ignore_https_errors=True)
        ctx.route('**/*',lambda route:route.continue_() if urlsplit(route.request.url).hostname=='127.0.0.1' else route.abort())
        page=ctx.new_page()
        page.goto(base+'/admin/login');page.locator('#username').fill('test-user');page.locator('#password').fill('test-pass')
        page.locator('.login-form button').click();page.wait_for_url(base+'/admin/')
        response=page.goto(base+'/admin/chatgpt')
        assert response.headers['referrer-policy']=='same-origin'
        assert response.headers['cache-control']=='no-store'
        with page.expect_response(lambda r:r.request.method=='POST' and '/admin/chatgpt' in r.url) as issued:
            page.locator('button[name="action"][value="rotate"]').click()
        assert issued.value.status==200,issued.value.status
        secret=page.get_by_label('새로 발급된 ChatGPT 연결 키').input_value()
        assert secret.startswith('hy_')
        with app.app_context():assert key_info(Profile.query.first())['hash']==digest(secret)
        # CSRF is still enforced; the dedicated API accepts only the new Bearer key.
        assert ctx.request.post(base+'/admin/chatgpt',form={'action':'rotate'}).status==400
        assert ctx.request.get(base+'/api/chatgpt/books',headers={'Authorization':'Bearer '+secret}).status==200
        assert ctx.request.get(base+'/api/chatgpt/books').status==401
        browser.close()
    print('PASS: real HTTPS key issuance, same-origin Referer, no-store, CSRF rejection without token, Bearer-only access.')
finally:
    server.shutdown();tmp.cleanup()
