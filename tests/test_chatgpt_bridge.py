"""Private, in-memory tests. Never read local env files or contact Notion/Storage."""
import re
import unittest
from pathlib import Path
from unittest.mock import patch

from flask import Blueprint, Flask, make_response, session
from flask_wtf.csrf import CSRFProtect

import chatgpt_bridge as bridge
from auth import admin_required, is_admin
from models import Archive, Book, Profile, ReadingNote, db


class ReadingBridgeTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__, root_path=str(Path(__file__).resolve().parents[1]))
        self.app.config.update(TESTING=True, SECRET_KEY='test-secret', SQLALCHEMY_DATABASE_URI='sqlite://',
                               SQLALCHEMY_TRACK_MODIFICATIONS=False, NOTION_TOKEN='', SITE_URL='https://portfolio.example')
        db.init_app(self.app)
        csrf = CSRFProtect(self.app)
        csrf.exempt(bridge.api)
        self.app.register_blueprint(bridge.api)
        admin = Blueprint('admin', __name__, url_prefix='/admin')
        @admin.route('/chatgpt', methods=['GET', 'POST'])
        @admin_required
        def chatgpt():
            return make_response(bridge.manage())
        for endpoint, path in [('dashboard', ''), ('login', '/login'), ('write', '/write'),
                               ('importer', '/import'), ('showcases', '/showcases'), ('comments', '/comments'), ('logout', '/logout')]:
            admin.add_url_rule(path, endpoint, lambda: 'OK')
        self.app.register_blueprint(admin)
        self.app.add_url_rule('/', 'home', lambda: 'home')
        self.app.jinja_env.filters.update(date=lambda x,*a:str(x), excerpt=lambda x,*a:str(x), minutes=lambda x:1, nl=lambda x:x)
        @self.app.context_processor
        def context():
            return {'is_admin': is_admin(), 'profile': Profile.query.first()}
        self.ctx = self.app.app_context(); self.ctx.push()
        db.create_all()
        self.key = 'hy_' + 'k' * 43
        profile = Profile(name='테스트', headline='독서', extra={bridge.KEY_FIELD: {'hash': bridge.digest(self.key)}})
        book = Book(title='원문 있는 책', author='저자', summary='원문 한 줄')
        db.session.add_all([profile, book]); db.session.flush()
        db.session.add(ReadingNote(book_id=book.id, title='실제 메모', summary='핵심 원문', my_thought='기록한 생각'))
        db.session.commit();self.book_id=book.id
        self.client = self.app.test_client()
        self.headers = {'Authorization': 'Bearer ' + self.key}
        self.base = f'/api/chatgpt/books/{book.id}'

    def tearDown(self):
        db.session.remove();db.drop_all();self.ctx.pop()

    def source(self):
        response = self.client.get(self.base + '/source', headers=self.headers)
        self.assertEqual(response.status_code, 200, response.json)
        return response.json

    def payload(self):
        return {'source_token':self.source()['source_token'], 'title':'요약 독서 노트', 'summary':'한 줄 핵심',
                'blocks':[{'type':'heading','text':'핵심 3개'}, {'type':'paragraph','text':'원문에 기반한 내용'}], 'tags':['독서']}

    def save(self, payload):
        return self.client.put(self.base + '/draft', headers=self.headers, json=payload)

    def test_private_api_rejects_missing_wrong_key_and_browser_session(self):
        for headers in [{}, {'Authorization':'Bearer wrong'}]:
            response=self.client.get('/api/chatgpt/books',headers=headers)
            self.assertEqual(response.status_code,401)
            self.assertEqual(response.headers['Cache-Control'],'no-store')
        with self.client.session_transaction() as s:s['admin']=True
        self.assertEqual(self.client.get('/api/chatgpt/books').status_code,401)
        self.assertEqual(self.client.get('/api/chatgpt/books',headers=self.headers).json['books'][0]['title'],'원문 있는 책')

    def test_source_read_returns_real_notes_and_does_not_create_posts(self):
        source=self.source()
        self.assertEqual(source['source_mode'],'imported_copy')
        self.assertIn('기록한 생각', str(source['blocks']))
        self.assertEqual(Archive.query.count(),0)
        self.assertNotIn(self.key,str(source))

    def test_create_is_private_retry_is_idempotent_and_existing_notes_preserved(self):
        original=Archive(title='기존 공개 원문',category='독서 노트',content_type='reading',status='published',book_id=self.book_id,source_type='notion')
        db.session.add(original);db.session.commit()
        payload=self.payload();first=self.save(payload)
        self.assertEqual(first.status_code,200,first.json)
        second=self.save(payload);self.assertEqual(second.json['id'],first.json['id'])
        self.assertTrue(second.json['unchanged']);self.assertEqual(Archive.query.count(),2)
        post=db.session.get(Archive,first.json['id']);self.assertEqual(post.status,'draft');self.assertFalse(post.is_visible)
        self.assertIn('/admin/write?',first.json['edit_url']);self.assertEqual(original.title,'기존 공개 원문')

    def test_updates_require_latest_revision_and_do_not_overwrite_manual_edits(self):
        payload=self.payload();saved=self.save(payload).json
        changed={**payload,'title':'고친 제목'}
        self.assertEqual(self.save(changed).status_code,409)
        changed['expected_revision']=saved['revision']
        updated=self.save(changed);self.assertEqual(updated.status_code,200,updated.json)
        post=db.session.get(Archive,saved['id']);post.title='홈페이지에서 직접 고침';db.session.commit()
        self.assertEqual(self.save(changed).status_code,409)
        self.assertEqual(post.title,'홈페이지에서 직접 고침')

    def test_publication_not_available_and_published_post_is_immutable(self):
        payload=self.payload()
        self.assertEqual(self.save({**payload,'status':'published'}).status_code,400)
        saved=self.save(payload).json
        post=db.session.get(Archive,saved['id']);post.status='published';db.session.commit()
        self.assertEqual(self.save(payload).status_code,409)

    def test_signed_source_cannot_be_forged_or_used_for_another_book(self):
        payload=self.payload();payload['source_token']='forged'
        self.assertEqual(self.save(payload).status_code,409)
        payload=self.payload();token=bridge.signer().dumps({'book_id':999,'page_id':'local','images':{}})
        self.assertEqual(self.save({**payload,'source_token':token}).status_code,403)
        with patch.object(bridge, 'SOURCE_TTL', -1):
            self.assertEqual(self.save(self.payload()).status_code,409)
        self.assertEqual(Archive.query.count(),0)

    def test_unknown_image_and_unsupported_html_block_are_rejected(self):
        payload=self.payload()
        self.assertEqual(self.save({**payload,'blocks':[{'type':'image','asset_id':'unknown'}]}).status_code,400)
        self.assertEqual(self.save({**payload,'blocks':[{'type':'markdown','text':'<script>alert(1)</script>'}]}).status_code,400)

    def test_selected_original_photo_is_copied_once_and_order_is_preserved(self):
        token=bridge.signer().dumps({'book_id':self.book_id,'page_id':'local','images':{'photo1':{'url':'https://file.notion.so/original.jpg','caption':'원본'}}})
        payload=self.payload();payload['source_token']=token
        payload['blocks'].insert(1,{'type':'image','asset_id':'photo1','caption':'선택한 사진'})
        with patch.object(bridge,'persist_image',return_value='https://storage.example/photo.jpg') as upload:
            first=self.save(payload);self.assertEqual(first.status_code,200,first.json)
            self.save(payload);self.assertEqual(upload.call_count,1)
        post=db.session.get(Archive,first.json['id'])
        self.assertEqual(post.blocks[1]['url'],'https://storage.example/photo.jpg')
        self.assertEqual(post.blocks[1]['caption'],'선택한 사진')

    def test_photo_failure_does_not_commit_partial_draft(self):
        payload=self.payload();payload['source_token']=bridge.signer().dumps({'book_id':self.book_id,'page_id':'local','images':{'p':{'url':'https://file.notion.so/a.jpg'}}})
        payload['blocks'].append({'type':'image','asset_id':'p'})
        with patch.object(bridge,'persist_image',side_effect=bridge.BridgeError('사진 복사 실패',422)):
            self.assertEqual(self.save(payload).status_code,422)
        self.assertEqual(Archive.query.count(),0)

    def test_blocked_image_download_never_contacts_network(self):
        for url in ['http://127.0.0.1/x','https://localhost/x','https://example.com/a.jpg','https://file.notion.so@127.0.0.1/a.jpg']:
            with patch('urllib.request.build_opener') as opener:
                with self.assertRaises(bridge.BridgeError):bridge.persist_image(url)
                opener.assert_not_called()

    def test_key_management_is_admin_only_csrf_protected_and_revocable(self):
        self.assertEqual(self.client.get('/admin/chatgpt').status_code,303)
        with self.client.session_transaction() as s:s['admin']=True
        self.assertEqual(self.client.post('/admin/chatgpt',data={'action':'rotate'}).status_code,400)
        page=self.client.get('/admin/chatgpt');self.assertEqual(page.status_code,200)
        csrf=re.search(r'name="csrf_token" value="([^"]+)"',page.text).group(1)
        rotated=self.client.post('/admin/chatgpt',data={'action':'rotate','csrf_token':csrf})
        self.assertEqual(rotated.status_code,200)
        raw=re.search(r'value="(hy_[A-Za-z0-9_-]+)"',rotated.text).group(1)
        self.assertNotIn(raw,str(Profile.query.first().extra))
        self.assertEqual(self.client.get('/api/chatgpt/books',headers=self.headers).status_code,401)
        new={'Authorization':'Bearer '+raw}
        self.assertEqual(self.client.get('/api/chatgpt/books',headers=new).status_code,200)
        self.client.post('/admin/chatgpt',data={'action':'revoke','csrf_token':csrf})
        self.assertEqual(self.client.get('/api/chatgpt/books',headers=new).status_code,401)

    def test_public_schema_has_bearer_auth_only_draft_write_and_no_secrets(self):
        response=self.client.get('/api/chatgpt/openapi.json')
        self.assertEqual(response.status_code,200)
        schema=response.json
        self.assertEqual(schema['servers'][0]['url'],'https://portfolio.example')
        self.assertEqual(schema['security'],[{'ReadingKey':[]}])
        write=schema['paths']['/api/chatgpt/books/{book_id}/draft']['put']
        self.assertTrue(write['x-openai-isConsequential'])
        self.assertNotIn('publish',schema['paths'])
        self.assertNotIn(self.key,response.text)

    def test_live_notion_reads_enforce_selected_book_ancestry(self):
        with patch.object(bridge.SourceClient,'request',return_value={'id':'b'*32,'parent':{'type':'database_id','database_id':'c'*32}}):
            self.app.config['NOTION_TOKEN']='fake'
            with self.assertRaises(bridge.BridgeError) as error:
                bridge.verified_page(bridge.SourceClient(),'a'*32,'b'*32)
            self.assertEqual(error.exception.status,403)


if __name__=='__main__':unittest.main()
