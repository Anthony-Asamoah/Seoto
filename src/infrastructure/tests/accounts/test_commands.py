from io import StringIO
from unittest import mock

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django_otp.plugins.otp_totp.models import TOTPDevice

from .helpers import current_token


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
