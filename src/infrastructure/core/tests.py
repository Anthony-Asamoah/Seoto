from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase, override_settings


class AdminLoginRecaptchaTests(TestCase):
    """The admin login carries the same reCAPTCHA v3 gate as the public auth forms."""

    def setUp(self):
        User.objects.create_superuser('boss', 'boss@example.com', 'pw12345678')

    def test_login_page_renders_the_recaptcha_partial(self):
        with override_settings(RECAPTCHA_SITE_KEY='site-key'):
            response = self.client.get('/admin/login/')

        self.assertContains(response, 'g-recaptcha-response-adminLoginForm')

    @override_settings(RECAPTCHA_ENABLED=True)
    @mock.patch('infrastructure.core.mixins.views.is_human', return_value=(False, 0.1))
    def test_failing_score_blocks_the_login(self, mock_is_human):
        response = self.client.post(
            '/admin/login/', {'username': 'boss', 'password': 'pw12345678'}
        )

        self.assertContains(response, 'Security verification failed')
        self.assertEqual(mock_is_human.call_args.kwargs['action'], 'admin_login')
        self.assertNotIn('_auth_user_id', self.client.session)

    @override_settings(RECAPTCHA_ENABLED=True)
    @mock.patch('infrastructure.core.mixins.views.is_human', return_value=(True, 0.9))
    def test_passing_score_falls_through_to_the_credential_check(self, _mock_is_human):
        response = self.client.post('/admin/login/', {'username': 'boss', 'password': 'wrong'})

        self.assertNotContains(response, 'Security verification failed')
        self.assertContains(response, 'Please enter the correct')

    @override_settings(RECAPTCHA_ENABLED=False)
    @mock.patch('infrastructure.core.mixins.views.is_human')
    def test_disabled_recaptcha_is_not_verified(self, mock_is_human):
        self.client.post('/admin/login/', {'username': 'boss', 'password': 'pw12345678'})

        mock_is_human.assert_not_called()
