"""Browser regression check using a temporary DB, generated test login, and local server.
Run with a Python environment containing requirements.txt and Playwright/Chrome.
"""
import os
import sys
import tempfile
import threading
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
tmp = tempfile.TemporaryDirectory(prefix='hy-writing-')
os.environ.update(ENV_FILE=str(Path(tmp.name)/'unused-env'), DATABASE_URL='sqlite:///'+str(Path(tmp.name)/'test.db'),
                  SECRET_KEY='browser-test-only-secret', NOTION_TOKEN='', SUPABASE_URL='', SUPABASE_SERVICE_KEY='')
from app import app
from models import db, Profile, Book, Archive, Project
from werkzeug.security import generate_password_hash
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright
app.config.update(TESTING=True, ADMIN_USERNAME='test-author', ADMIN_PASSWORD_HASH=generate_password_hash('test-pass-only'), SESSION_COOKIE_SECURE=False)
with app.app_context():
    db.create_all()
    db.session.add(Profile(name='검증 사용자',headline='검증',extra={}))
    book=Book(title='검증 도서',author='검증 저자');db.session.add(book);db.session.flush()
    reading=Archive(title='기존 독서 노트',category='독서 노트',content_type='reading',status='draft',book_id=book.id,
                    blocks=[{'type':'paragraph','text':'기존 본문'},{'type':'image','url':'/static/images/slow-bookshop.jpg','caption':'원본 사진'}])
    published=Archive(title='공개된 글',category='독서 노트',content_type='reading',status='published',book_id=book.id,blocks=[{'type':'paragraph','text':'공개 원문'}])
    notes=Archive(title='기록 초안',category='DATA',content_type='notes',status='draft',blocks=[{'type':'paragraph','text':'기록 본문'}])
    project=Project(title='검증 프로젝트',status='draft',problem='검증 문제',role='기획',tech_stack='Python',blocks=[])
    db.session.add_all([reading,published,notes,project]);db.session.commit()
    ids={'reading':reading.id,'published':published.id,'notes':notes.id,'project':project.id}
server=make_server('127.0.0.1',0,app,threaded=True)
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
base=f'http://127.0.0.1:{server.server_port}'
out=root/'artifacts/writing-steps';out.mkdir(parents=True,exist_ok=True)
errors=[]
try:
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless=True)
        context=browser.new_context(viewport={'width':1440,'height':1050})
        context.route('**/*',lambda route: route.continue_() if urlsplit(route.request.url).hostname=='127.0.0.1' else route.abort())
        page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(base+'/admin/login');page.locator('#username').fill('test-author');page.locator('#password').fill('test-pass-only')
        page.locator('.login-form button').click();page.wait_for_url(base+'/admin/')
        # Each kind opens with a real, independently reloadable stage URL.
        for kind in ['notes','reading','project','about']:
            page.goto(base+f'/admin/write?kind={kind}')
            page.locator('#stage-title').wait_for()
            page.wait_for_function('document.querySelector("#stage-title").textContent.length > 0')
            for stage in ['details','content','media','publish']:
                page.locator(f'[data-stage-link="{stage}"]').click()
                assert parse_qs(urlsplit(page.url).query)['step']==[stage]
                assert page.locator('#studio').get_attribute('data-step')==stage
                if stage=='publish':
                    assert page.locator('#canvas [contenteditable="true"], #canvas [contenteditable="plaintext-only"]').count()==0
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),(kind,stage)
            page.reload();page.wait_for_function('document.querySelector("#studio").dataset.step==="publish"')
        # A new post keeps unsaved text through forward/back navigation, then autosave retains the current stage.
        page.goto(base+'/admin/write?kind=reading&step=details')
        page.locator('.post-title').fill('단계별 새 독서 노트')
        page.locator('#stage-next').click()
        page.locator('.blk-paragraph [contenteditable]').first.fill('단계를 옮겨도 남는 본문')
        page.locator('#stage-next').click();page.locator('#stage-next').click()
        assert '단계를 옮겨도 남는 본문' in page.locator('#canvas').inner_text()
        page.wait_for_function('new URL(location.href).searchParams.has("id")')
        assert parse_qs(urlsplit(page.url).query)['step']==['publish']
        page.go_back();page.wait_for_function('document.querySelector("#studio").dataset.step==="media"')
        page.go_back();page.wait_for_function('document.querySelector("#studio").dataset.step==="content"')
        assert page.locator('.blk-paragraph [contenteditable]').first.inner_text()=='단계를 옮겨도 남는 본문'
        page.locator('[data-stage-link="details"]').click();assert page.locator('.post-title').inner_text()=='단계별 새 독서 노트'
        # Existing editors open on content; saving keeps the requested stage and does not erase other parts.
        page.goto(base+f'/admin/write?kind=reading&id={ids["reading"]}')
        page.wait_for_function('document.querySelector("#stage-title").textContent.length > 0')
        assert page.locator('#studio').get_attribute('data-step')=='content'
        page.locator('.blk-paragraph [contenteditable]').first.fill('수정한 본문')
        page.locator('[data-stage-link="media"]').click()
        assert page.locator('.stage-media-item img').count()==1
        page.locator('[data-action="draft"]').first.click()
        page.wait_for_url('**/admin/write?**step=media')
        with app.app_context():
            post=db.session.get(Archive,ids['reading']);assert post.title=='기존 독서 노트'
            assert post.blocks[0]['text']=='수정한 본문';assert post.blocks[1]['caption']=='원본 사진'
        # Screenshots, PC and mobile, and a published edit must not automatically go live.
        for width,name in [(1440,'desktop'),(390,'mobile')]:
            page.set_viewport_size({'width':width,'height':1000})
            for stage in ['details','content','media','publish']:
                page.locator(f'[data-stage-link="{stage}"]').click()
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),(name,stage)
                page.screenshot(path=str(out/f'{name}-{stage}.png'),full_page=True)
        page.goto(base+f'/admin/write?kind=reading&id={ids["published"]}&step=content')
        page.locator('.blk-paragraph [contenteditable]').first.fill('아직 공개하지 않은 수정')
        page.locator('[data-stage-link="publish"]').click()
        page.wait_for_timeout(3500)
        with app.app_context():
            post=db.session.get(Archive,ids['published']);assert post.blocks[0]['text']=='공개 원문'
        page.locator('#publish-pop [data-action="publish"]').click()
        page.wait_for_url('**/admin/write?**step=publish')
        with app.app_context():
            post=db.session.get(Archive,ids['published']);assert post.blocks[0]['text']=='아직 공개하지 않은 수정'
            assert post.status=='published'
        assert not errors,errors
        browser.close()
    print('PASS: four kinds × four stage URLs; forward/back; new-post autosave; stage-preserving save; media preservation; PC/mobile layout; published edits remain private.')
finally:
    server.shutdown();tmp.cleanup()
