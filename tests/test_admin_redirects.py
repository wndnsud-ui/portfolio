"""Regression checks for expired-session submissions and login return URLs."""
import unittest
from urllib.parse import parse_qs, urlsplit
from flask import Flask
from auth import admin_required, admin_return_url


class AdminRedirectTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.secret_key = 'test-only'
        self.app.add_url_rule('/admin', 'admin.dashboard', lambda: 'dashboard')
        self.app.add_url_rule('/admin/login', 'admin.login', lambda: 'login')
        self.app.add_url_rule('/admin/showcases', 'admin.showcases', admin_required(lambda: 'showcases'))
        self.app.add_url_rule('/admin/showcases/rest/videos', 'admin.add_video', admin_required(lambda: 'saved'), methods=['POST'])

    def test_expired_post_returns_to_get_page_without_replaying_save(self):
        client = self.app.test_client()
        response = client.post('/admin/showcases/rest/videos', data={'url': 'example'})
        self.assertEqual(response.status_code, 303)
        target = parse_qs(urlsplit(response.location).query)['next'][0]
        self.assertEqual(target, '/admin')
        self.assertEqual(client.get(target).status_code, 200)
        with client.session_transaction() as state:
            self.assertIn('저장하지 못했어요', state['_flashes'][0][1])

    def test_get_return_keeps_query(self):
        response = self.app.test_client().get('/admin/showcases?s=rest')
        self.assertEqual(parse_qs(urlsplit(response.location).query)['next'], ['/admin/showcases?s=rest'])

    def test_login_return_rejects_actions_unknown_and_external_urls(self):
        with self.app.test_request_context('/'):
            for target in ['/admin/showcases/rest/videos', '/admin/missing', '/administrator', '//example.com/admin/a', 'https://example.com/admin/a', '/admin/login', None]:
                with self.subTest(target=target):
                    self.assertEqual(admin_return_url(target), '/admin')
            self.assertEqual(admin_return_url('/admin/showcases?s=rest#videos'), '/admin/showcases?s=rest#videos')

    def test_authenticated_submission_is_unchanged(self):
        client = self.app.test_client()
        with client.session_transaction() as state:
            state['admin'] = True
        self.assertEqual(client.post('/admin/showcases/rest/videos').data, b'saved')


if __name__ == '__main__':
    unittest.main()
