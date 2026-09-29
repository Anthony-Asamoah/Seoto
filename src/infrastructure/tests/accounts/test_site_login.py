from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django_otp.plugins.otp_totp.models import TOTPDevice

from .helpers import current_token
from .test_admin_login import make_passkey


class SiteLoginTests(TestCase):
    """/accounts/login/ honours the same optional-but-binding second factor as the admin."""

    def setUp(self):
        cache.clear()
        self.password = 'sup3r-s3cret-pw'
        self.user = User.objects.create_user('member', 'm@example.com', self.password)
        self.url = reverse('login')

    def post_login(self, **extra):
        return self.client.post(self.url, {'username': 'member', 'password': self.password, **extra})

    def test_password_alone_logs_in_without_a_device(self):
        self.assertEqual(self.post_login().status_code, 302)
        self.assertIn('_auth_user_id', self.client.session)

    def test_enrolled_account_needs_the_code(self):
        TOTPDevice.objects.create(user=self.user, name='Authenticator', confirmed=True)

        response = self.post_login()

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertContains(response, 'otp-reveal is-open')

    def test_enrolled_account_logs_in_with_a_valid_code(self):
        device = TOTPDevice.objects.create(user=self.user, name='Authenticator', confirmed=True)

        response = self.post_login(otp_token=current_token(device))

        self.assertEqual(response.status_code, 302)
        self.assertIn('_auth_user_id', self.client.session)

    def test_wrong_code_is_rejected(self):
        TOTPDevice.objects.create(user=self.user, name='Authenticator', confirmed=True)

        self.post_login(otp_token='000000')

        self.assertNotIn('_auth_user_id', self.client.session)

    def test_passkey_only_account_cannot_use_a_password(self):
        make_passkey(self.user)

        response = self.post_login()

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertContains(response, 'This account signs in with a passkey.')

    def test_page_offers_passkey_sign_in_and_a_collapsed_code_field(self):
        response = self.client.get(self.url)

        self.assertContains(response, 'id="passkey-verification-button"')
        self.assertContains(response, 'id="otpReveal"')
        self.assertNotContains(response, 'otp-reveal is-open')

    def test_bad_password_still_shows_the_generic_message(self):
        response = self.client.post(self.url, {'username': 'member', 'password': 'wrong'})

        self.assertContains(response, 'Incorrect username or password')

    def test_factors_lookup_reports_enrolment(self):
        TOTPDevice.objects.create(user=self.user, name='Authenticator', confirmed=True)
        User.objects.create_user('plain', password=self.password)
        lookup = reverse('login_factors')

        self.assertEqual(self.client.post(lookup, {'username': 'member'}).json(), {'code': True, 'passkey_only': False})
        self.assertEqual(self.client.post(lookup, {'username': 'plain'}).json(), {'code': False, 'passkey_only': False})
        self.assertEqual(self.client.post(lookup, {'username': 'ghost'}).json(), {'code': False, 'passkey_only': False})
