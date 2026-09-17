from unittest import mock

from django.contrib.auth.models import User
from django.core import mail
from django.core.cache import cache
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django_otp.plugins.otp_static.models import StaticDevice
from django_otp.plugins.otp_totp.models import TOTPDevice

from domains.accounts import services

from .helpers import current_token


class TOTPSetupServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('enrollee', 'enrollee@example.com', 'pw-pw-pw-pw')

    def test_issuing_replaces_every_existing_device(self):
        stale = TOTPDevice.objects.create(user=self.user, name='Old phone', confirmed=True)

        device = services.issue_totp_device(self.user)

        self.assertFalse(TOTPDevice.objects.filter(pk=stale.pk).exists())
        self.assertEqual(TOTPDevice.objects.filter(user=self.user).count(), 1)
        self.assertNotEqual(device.key, stale.key)
        self.assertFalse(device.confirmed)

    def test_backup_codes_replace_the_previous_set(self):
        first = services.issue_backup_codes(self.user)

        second = services.issue_backup_codes(self.user)

        self.assertEqual(len(second), services.BACKUP_CODE_COUNT)
        self.assertEqual(sorted(services.backup_codes(self.user)), sorted(second))
        self.assertFalse(set(first) & set(second))

    def test_backup_device_is_confirmed_so_the_codes_can_sign_in(self):
        services.issue_backup_codes(self.user)

        self.assertTrue(
            StaticDevice.objects.get(user=self.user, name=services.BACKUP_DEVICE_NAME).confirmed
        )

    def test_setup_token_round_trips(self):
        device = services.issue_totp_device(self.user)

        self.assertEqual(services.read_setup_token(services.make_setup_token(device)), device)

    def test_tampered_token_is_rejected(self):
        device = services.issue_totp_device(self.user)

        self.assertIsNone(services.read_setup_token(services.make_setup_token(device) + 'x'))

    def test_expired_token_is_rejected(self):
        device = services.issue_totp_device(self.user)
        token = services.make_setup_token(device)

        with mock.patch.object(services, 'SETUP_LINK_MAX_AGE', -1):
            self.assertIsNone(services.read_setup_token(token))

    def test_token_dies_once_the_device_is_confirmed(self):
        device = services.issue_totp_device(self.user)
        token = services.make_setup_token(device)
        services.confirm_device(device, current_token(device))

        self.assertIsNone(services.read_setup_token(token))

    def test_confirm_device_rejects_a_wrong_code(self):
        device = services.issue_totp_device(self.user)

        self.assertFalse(services.confirm_device(device, '000000'))
        self.assertFalse(TOTPDevice.objects.get(pk=device.pk).confirmed)

    def test_qr_svg_is_inline_markup_for_the_config_url(self):
        device = services.issue_totp_device(self.user)

        svg = services.qr_svg(device.config_url)

        self.assertTrue(svg.startswith('<svg'))
        self.assertNotIn('<?xml', svg)


class AdminTOTPSetupViewTests(TestCase):
    """The admin-side enrolment endpoints hanging off the User change page."""

    def setUp(self):
        cache.clear()
        self.admin = User.objects.create_superuser('root', 'root@example.com', 'pw-pw-pw-pw')
        self.device = TOTPDevice.objects.create(user=self.admin, name='Authenticator', confirmed=True)
        self.client.post(
            reverse('admin:login'),
            {'username': 'root', 'password': 'pw-pw-pw-pw', 'otp_token': current_token(self.device)},
        )
        self.target = User.objects.create_user('enrollee', 'enrollee@example.com', 'pw-pw-pw-pw')
        self.setup_url = reverse('admin:auth_user_totp_setup', args=[self.target.pk])
        self.verify_url = reverse('admin:auth_user_totp_verify', args=[self.target.pk])

    def test_change_page_offers_the_button(self):
        response = self.client.get(reverse('admin:auth_user_change', args=[self.target.pk]))

        self.assertContains(response, 'totp-setup-btn')
        self.assertContains(response, 'Set up 2FA')

    def test_button_label_tracks_the_enrolment_state(self):
        services.issue_totp_device(self.target)
        response = self.client.get(reverse('admin:auth_user_change', args=[self.target.pk]))
        self.assertContains(response, 'Resume 2FA setup')

        TOTPDevice.objects.filter(user=self.target).update(confirmed=True)
        response = self.client.get(reverse('admin:auth_user_change', args=[self.target.pk]))
        self.assertContains(response, 'Reset 2FA')

    def test_change_page_loads_the_scripts_the_button_needs(self):
        """csrf.js only reaches the admin through CustomUserAdmin.Media."""
        response = self.client.get(reverse('admin:auth_user_change', args=[self.target.pk]))

        self.assertContains(response, 'js/csrf')
        self.assertContains(response, 'js/admin_totp')
        self.assertContains(response, 'totpSetupModal')

    def test_changelist_flags_who_is_enrolled(self):
        TOTPDevice.objects.create(user=self.target, name='Authenticator', confirmed=True)
        url = reverse('admin:auth_user_changelist')

        rows = {user.username: user._has_2fa for user in self.client.get(url).context['cl'].result_list}

        self.assertTrue(rows['enrollee'])
        self.assertTrue(rows['root'])

    def test_changelist_queries_do_not_grow_with_the_number_of_users(self):
        """user_icon and has_2fa would each cost a query per row without get_queryset."""
        url = reverse('admin:auth_user_changelist')
        self.client.get(url)

        with CaptureQueriesContext(connection) as few:
            self.client.get(url)

        for name in 'abcdefgh':
            User.objects.create_user(name, f'{name}@example.com', 'pw-pw-pw-pw')

        with CaptureQueriesContext(connection) as many:
            self.client.get(url)

        self.assertEqual(len(many.captured_queries), len(few.captured_queries))

    def test_get_is_not_allowed(self):
        self.assertEqual(self.client.get(self.setup_url).status_code, 405)

    def test_first_setup_issues_a_device_and_backup_codes(self):
        response = self.client.post(self.setup_url)

        self.assertContains(response, '<svg')
        device = TOTPDevice.objects.get(user=self.target)
        self.assertFalse(device.confirmed)
        self.assertEqual(len(services.backup_codes(self.target)), services.BACKUP_CODE_COUNT)
        self.assertContains(response, services.secret_b32(device))

    def test_pending_device_is_reshown_without_rotating(self):
        first = services.issue_totp_device(self.target)

        self.client.post(self.setup_url)

        self.assertEqual(TOTPDevice.objects.get(user=self.target).key, first.key)

    def test_confirmed_device_forces_a_confirmation_step(self):
        existing = TOTPDevice.objects.create(user=self.target, name='Authenticator', confirmed=True)

        response = self.client.post(self.setup_url)

        self.assertContains(response, 'totp-confirm-reset')
        self.assertEqual(TOTPDevice.objects.get(user=self.target).key, existing.key)

    def test_confirmed_reset_rotates_the_secret(self):
        existing = TOTPDevice.objects.create(user=self.target, name='Authenticator', confirmed=True)

        response = self.client.post(self.setup_url, {'confirm': '1'})

        self.assertContains(response, '<svg')
        device = TOTPDevice.objects.get(user=self.target)
        self.assertNotEqual(device.key, existing.key)
        self.assertFalse(device.confirmed)

    def test_verify_activates_the_device(self):
        device = services.issue_totp_device(self.target)

        response = self.client.post(self.verify_url, {'code': current_token(device)})

        self.assertTrue(response.json()['ok'])
        self.assertTrue(TOTPDevice.objects.get(pk=device.pk).confirmed)

    def test_verify_rejects_a_wrong_code(self):
        device = services.issue_totp_device(self.target)

        response = self.client.post(self.verify_url, {'code': '000000'})

        self.assertFalse(response.json()['ok'])
        self.assertFalse(TOTPDevice.objects.get(pk=device.pk).confirmed)

    def test_staff_without_change_user_permission_is_refused(self):
        cache.clear()
        weak = User.objects.create_user('weak', 'weak@example.com', 'pw-pw-pw-pw', is_staff=True)
        weak_device = TOTPDevice.objects.create(user=weak, name='Authenticator', confirmed=True)
        self.client.logout()
        self.client.post(
            reverse('admin:login'),
            {'username': 'weak', 'password': 'pw-pw-pw-pw', 'otp_token': current_token(weak_device)},
        )

        self.assertEqual(self.client.post(self.setup_url).status_code, 403)

    def test_anonymous_visitor_is_sent_to_the_admin_login(self):
        self.client.logout()

        response = self.client.post(self.setup_url)

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('admin:login'), response.url)


class TOTPSetupEmailTests(TestCase):
    def setUp(self):
        cache.clear()
        self.admin = User.objects.create_superuser('root', 'root@example.com', 'pw-pw-pw-pw')
        device = TOTPDevice.objects.create(user=self.admin, name='Authenticator', confirmed=True)
        self.client.post(
            reverse('admin:login'),
            {'username': 'root', 'password': 'pw-pw-pw-pw', 'otp_token': current_token(device)},
        )
        self.target = User.objects.create_user('enrollee', 'enrollee@example.com', 'pw-pw-pw-pw')
        self.email_url = reverse('admin:auth_user_totp_email', args=[self.target.pk])

    def test_email_carries_the_link_but_never_the_secret(self):
        device = services.issue_totp_device(self.target)

        response = self.client.post(self.email_url)

        self.assertTrue(response.json()['ok'])
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertEqual(sent.to, ['enrollee@example.com'])
        bodies = sent.body + sent.alternatives[0][0]
        self.assertIn('/accounts/2fa/setup/', bodies)
        self.assertNotIn(services.secret_b32(device), bodies)
        self.assertNotIn('<svg', bodies)

    def test_link_in_the_email_resolves_to_the_pending_device(self):
        device = services.issue_totp_device(self.target)
        self.client.post(self.email_url)

        token = mail.outbox[0].body.split('/accounts/2fa/setup/')[1].split('\n')[0].strip('/ ')

        self.assertEqual(services.read_setup_token(token), device)

    def test_nothing_is_sent_without_an_email_address(self):
        services.issue_totp_device(self.target)
        User.objects.filter(pk=self.target.pk).update(email='')

        response = self.client.post(self.email_url)

        self.assertFalse(response.json()['ok'])
        self.assertEqual(mail.outbox, [])

    def test_nothing_is_sent_without_a_pending_device(self):
        response = self.client.post(self.email_url)

        self.assertFalse(response.json()['ok'])
        self.assertEqual(mail.outbox, [])


class TOTPSetupConfirmViewTests(TestCase):
    """The public enrolment page the emailed link lands on."""

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user('enrollee', 'enrollee@example.com', 'pw-pw-pw-pw')
        self.device = services.issue_totp_device(self.user)
        self.codes = services.issue_backup_codes(self.user)
        self.url = reverse('totp_setup_confirm', args=[services.make_setup_token(self.device)])

    def test_valid_link_shows_the_qr_secret_and_codes(self):
        response = self.client.get(self.url)

        self.assertContains(response, '<svg')
        self.assertContains(response, services.secret_b32(self.device))
        self.assertContains(response, self.codes[0])

    def test_wrong_code_re_renders_with_an_error(self):
        response = self.client.post(self.url, {'code': '000000'})

        self.assertContains(response, 'did not match')
        self.assertFalse(TOTPDevice.objects.get(pk=self.device.pk).confirmed)

    def test_valid_code_activates_the_device(self):
        response = self.client.post(self.url, {'code': current_token(self.device)})

        self.assertRedirects(response, reverse('totp_setup_done'))
        self.assertTrue(TOTPDevice.objects.get(pk=self.device.pk).confirmed)

    def test_link_is_dead_after_activation(self):
        self.client.post(self.url, {'code': current_token(self.device)})

        response = self.client.get(self.url)

        self.assertContains(response, 'Setup Link Expired')

    def test_forged_token_shows_the_expired_page(self):
        response = self.client.get(reverse('totp_setup_confirm', args=['not-a-real-token']))

        self.assertContains(response, 'Setup Link Expired')
