from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django_otp.plugins.otp_totp.models import TOTPDevice

from domains.accounts import services

from .helpers import current_token

PASSWORD = 'pw-pw-pw-pw'


class ProfileAccessTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('owner', 'owner@example.com', PASSWORD)
        self.other = User.objects.create_user('other', 'other@example.com', PASSWORD)
        self.client.force_login(self.other)

    def test_another_users_profile_redirects_to_your_own(self):
        response = self.client.get(reverse('profile', args=['owner']))

        self.assertRedirects(response, reverse('profile', args=['other']), fetch_redirect_response=False)

    def test_posting_to_another_users_profile_changes_nothing(self):
        self.client.post(reverse('profile', args=['owner']), {
            'first_name': 'x', 'last_name': 'x', 'email': 'attacker@example.com', 'contact': '', 'picture': '',
        })

        self.owner.refresh_from_db()
        self.assertEqual(self.owner.email, 'owner@example.com')

    @override_settings(STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    })
    def test_own_profile_shows_security_settings(self):
        response = self.client.get(reverse('profile', args=['other']))

        self.assertContains(response, reverse('self_totp_setup'))
        self.assertContains(response, 'passkey-registration-placeholder')


class SelfTOTPSetupTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('self', 'self@example.com', PASSWORD)
        self.client.force_login(self.user)

    def test_requires_login(self):
        self.client.logout()

        response = self.client.post(reverse('self_totp_setup'))

        self.assertEqual(response.status_code, 302)
        self.assertFalse(TOTPDevice.objects.exists())

    def test_get_is_refused(self):
        self.assertEqual(self.client.get(reverse('self_totp_setup')).status_code, 405)

    def test_setup_then_verify_activates_and_verifies_session(self):
        response = self.client.post(reverse('self_totp_setup'))
        self.assertContains(response, 'Scan this with your authenticator app')
        self.assertNotContains(response, 'totp-email')
        device = services.pending_device(self.user)

        response = self.client.post(reverse('self_totp_verify'), {'code': current_token(device)})

        self.assertTrue(response.json()['ok'])
        self.assertTrue(services.has_confirmed_device(self.user))
        self.assertEqual(self.client.session.get('otp_device_id'), device.persistent_id)

    def test_wrong_code_is_rejected(self):
        self.client.post(reverse('self_totp_setup'))

        response = self.client.post(reverse('self_totp_verify'), {'code': '000000'})

        self.assertFalse(response.json()['ok'])
        self.assertFalse(services.has_confirmed_device(self.user))

    def test_unverified_session_cannot_replace_an_enrolled_authenticator(self):
        existing = services.issue_totp_device(self.user, confirmed=True)

        response = self.client.post(reverse('self_totp_setup'), {'confirm': '1'})

        self.assertEqual(response.status_code, 403)
        self.assertTrue(TOTPDevice.objects.filter(pk=existing.pk, confirmed=True).exists())

    def test_verified_session_must_confirm_before_reset(self):
        existing = services.issue_totp_device(self.user, confirmed=True)
        self._verify_session(existing)

        response = self.client.post(reverse('self_totp_setup'))

        self.assertContains(response, 'You already have a working authenticator')
        self.assertTrue(TOTPDevice.objects.filter(pk=existing.pk).exists())

        self.client.post(reverse('self_totp_setup'), {'confirm': '1'})

        self.assertFalse(TOTPDevice.objects.filter(pk=existing.pk).exists())
        self.assertIsNotNone(services.pending_device(self.user))

    def _verify_session(self, device):
        session = self.client.session
        session['otp_device_id'] = device.persistent_id
        session.save()
