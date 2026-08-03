from io import StringIO
from unittest import mock

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse
from django_otp.oath import TOTP
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice


def current_token(device):
    totp = TOTP(device.bin_key, device.step, device.t0, device.digits, device.drift)
    return format(totp.token(), f'0{device.digits}d')


class AdminTOTPLoginTests(TestCase):
    """The admin is gated on a verified OTP device, not just a password."""

    def setUp(self):
        # RateLimitMiddleware counts POSTs to /admin/login/ in a process-wide LocMemCache.
        cache.clear()
        self.password = 'sup3r-s3cret-pw'
        self.user = User.objects.create_superuser(
            username='admin_user', email='admin@example.com', password=self.password
        )
        self.device = TOTPDevice.objects.create(user=self.user, name='Authenticator', confirmed=True)
        self.login_url = reverse('admin:login')

    def post_login(self, **extra):
        data = {'username': self.user.username, 'password': self.password}
        data.update(extra)
        return self.client.post(self.login_url, data)

    def test_password_alone_is_rejected(self):
        response = self.post_login()

        self.assertEqual(response.status_code, 200)
        self.assertIn('Please enter your OTP token.', response.context['form'].non_field_errors())
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_wrong_token_is_rejected(self):
        response = self.post_login(otp_token='000000')

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            'Invalid token. Please make sure you have entered it correctly.',
            response.context['form'].non_field_errors(),
        )
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_valid_token_logs_in_and_reaches_admin(self):
        response = self.post_login(otp_token=current_token(self.device))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get(reverse('admin:index')).status_code, 200)

    def test_static_backup_token_is_accepted(self):
        static_device = StaticDevice.objects.create(user=self.user, name='Backup codes')
        StaticToken.objects.create(device=static_device, token='abcd1234')

        response = self.post_login(otp_token='abcd1234')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get(reverse('admin:index')).status_code, 200)

    def test_backup_token_is_single_use(self):
        static_device = StaticDevice.objects.create(user=self.user, name='Backup codes')
        StaticToken.objects.create(device=static_device, token='abcd1234')
        self.post_login(otp_token='abcd1234')
        self.client.logout()

        self.post_login(otp_token='abcd1234')

        self.assertNotIn('_auth_user_id', self.client.session)

    def test_session_authenticated_without_otp_is_denied(self):
        """force_login bypasses the OTP form, so the admin site itself must still refuse."""
        self.client.force_login(self.user)

        response = self.client.get(reverse('admin:index'))

        self.assertEqual(response.status_code, 302)
        self.assertIn(self.login_url, response.url)

    def test_login_page_offers_the_token_field(self):
        response = self.client.get(self.login_url)

        self.assertContains(response, 'name="otp_token"')


class SetupAdminTOTPCommandTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username='admin_user', email='admin@example.com', password='sup3r-s3cret-pw'
        )

    def test_noinput_creates_a_confirmed_device(self):
        call_command('setup_admin_totp', 'admin_user', '--noinput', stdout=StringIO())

        device = TOTPDevice.objects.get(user=self.user)
        self.assertEqual(device.name, 'Authenticator')
        self.assertTrue(device.confirmed)

    def test_unknown_user_is_reported(self):
        with self.assertRaises(CommandError):
            call_command('setup_admin_totp', 'nobody', '--noinput', stdout=StringIO())

    def test_duplicate_name_requires_reset(self):
        call_command('setup_admin_totp', 'admin_user', '--noinput', stdout=StringIO())

        with self.assertRaises(CommandError):
            call_command('setup_admin_totp', 'admin_user', '--noinput', stdout=StringIO())

    def test_reset_replaces_the_secret(self):
        call_command('setup_admin_totp', 'admin_user', '--noinput', stdout=StringIO())
        original_key = TOTPDevice.objects.get(user=self.user).key

        call_command('setup_admin_totp', 'admin_user', '--noinput', '--reset', stdout=StringIO())

        self.assertEqual(TOTPDevice.objects.filter(user=self.user).count(), 1)
        self.assertNotEqual(TOTPDevice.objects.get(user=self.user).key, original_key)

    def test_prompted_confirmation_requires_a_working_code(self):
        with mock.patch('builtins.input', return_value='000000'):
            with self.assertRaises(CommandError):
                call_command('setup_admin_totp', 'admin_user', stdout=StringIO())

        self.assertFalse(TOTPDevice.objects.filter(user=self.user).exists())

    def test_prompted_confirmation_activates_the_device(self):
        def answer(_prompt):
            return current_token(TOTPDevice.objects.get(user=self.user))

        with mock.patch('builtins.input', side_effect=answer):
            call_command('setup_admin_totp', 'admin_user', stdout=StringIO())

        self.assertTrue(TOTPDevice.objects.get(user=self.user).confirmed)
