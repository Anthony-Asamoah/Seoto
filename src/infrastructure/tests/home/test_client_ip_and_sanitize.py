from django.template import Context, Template
from django.test import RequestFactory, TestCase, override_settings

from domains.home.utils import get_client_ip


class ClientIpTests(TestCase):
    def ip(self, **meta):
        return get_client_ip(RequestFactory().get('/', **meta))

    def test_spoofed_left_entry_is_ignored_behind_cloudflare(self):
        self.assertEqual(self.ip(HTTP_X_FORWARDED_FOR='6.6.6.6, 1.2.3.4, 172.64.0.1'), '1.2.3.4')

    def test_direct_hit_uses_only_entry(self):
        self.assertEqual(self.ip(HTTP_X_FORWARDED_FOR='9.9.9.9'), '9.9.9.9')

    def test_no_header_falls_back_to_remote_addr(self):
        self.assertEqual(self.ip(REMOTE_ADDR='10.0.0.5'), '10.0.0.5')

    @override_settings(CLIENT_IP_PROXY_HOPS=0)
    def test_no_cloudflare_takes_last_entry(self):
        self.assertEqual(self.ip(HTTP_X_FORWARDED_FOR='6.6.6.6, 1.2.3.4'), '1.2.3.4')


class IncomingWebhookTests(TestCase):
    @override_settings(INCOMING_WEBHOOK_SECRET='')
    def test_closed_when_secret_unset(self):
        self.assertEqual(self.client.post('/home/incoming').status_code, 403)

    @override_settings(INCOMING_WEBHOOK_SECRET='s3cret')
    def test_wrong_secret_rejected(self):
        self.assertEqual(self.client.post('/home/incoming', HTTP_X_WEBHOOK_SECRET='nope').status_code, 403)
        self.assertEqual(self.client.post('/home/incoming').status_code, 403)


class SanitizeTests(TestCase):
    def render(self, tag, value):
        return Template('{% load sanitize %}{{ v|' + tag + ' }}').render(Context({'v': value}))

    def test_strips_script_and_handlers(self):
        out = self.render('sanitize', '<b>ok</b><script>alert(1)</script><img src=x onerror=alert(1)>')
        self.assertIn('<b>ok</b>', out)
        self.assertNotIn('script', out)
        self.assertNotIn('onerror', out)

    def test_rich_keeps_video_drops_js_urls(self):
        out = self.render('sanitize_rich', '<video controls src="https://x/y.mp4"></video><a href="javascript:alert(1)">a</a>')
        self.assertIn('<video', out)
        self.assertNotIn('javascript:', out)

    def test_rich_blocks_non_https_iframe(self):
        self.assertNotIn('javascript', self.render('sanitize_rich', '<iframe src="javascript:alert(1)"></iframe>'))
