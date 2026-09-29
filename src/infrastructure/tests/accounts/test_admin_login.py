from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice

from .helpers import current_token


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


class AdminOptionalTOTPTests(TestCase):
    """Accounts that never enrolled sign in on a password; enrolment is what makes the code mandatory."""

    def setUp(self):
        cache.clear()
        self.password = 'sup3r-s3cret-pw'
        self.user = User.objects.create_superuser(
            username='plain_admin', email='plain@example.com', password=self.password
        )
        self.login_url = reverse('admin:login')

    def post_login(self, **extra):
        return self.client.post(
            self.login_url, {'username': self.user.username, 'password': self.password, **extra}
        )

    def test_password_alone_logs_in_without_a_device(self):
        response = self.post_login()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get(reverse('admin:index')).status_code, 200)

    def test_unconfirmed_device_does_not_gate_login(self):
        TOTPDevice.objects.create(user=self.user, name='Authenticator', confirmed=False)
        StaticDevice.objects.create(user=self.user, name='Backup codes', confirmed=True)

        self.assertEqual(self.post_login().status_code, 302)

    def test_confirming_a_device_makes_the_code_mandatory(self):
        TOTPDevice.objects.create(user=self.user, name='Authenticator', confirmed=True)

        response = self.post_login()

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_session_from_before_enrolment_is_cut_off(self):
        self.post_login()
        TOTPDevice.objects.create(user=self.user, name='Authenticator', confirmed=True)

        response = self.client.get(reverse('admin:index'))

        self.assertEqual(response.status_code, 302)
        self.assertIn(self.login_url, response.url)

    def test_token_input_is_not_marked_required(self):
        html = self.client.get(self.login_url).content.decode()
        token_input = html[html.index('name="otp_token"'):].split('>', 1)[0]

        self.assertNotIn('required', token_input)


def make_passkey(user, confirmed=True):
    from django_otp_webauthn.models import WebAuthnCredential

    return WebAuthnCredential.objects.create(
        user=user, name='Passkey', confirmed=confirmed,
        credential_id=b'cred-' + str(user.pk).encode(), public_key=b'pk', sign_count=0,
    )


class AdminPasskeyTests(TestCase):
    def setUp(self):
        cache.clear()
        self.password = 'sup3r-s3cret-pw'
        self.user = User.objects.create_superuser(
            username='pk_admin', email='pk@example.com', password=self.password
        )
        self.login_url = reverse('admin:login')

    def post_login(self, **extra):
        return self.client.post(
            self.login_url, {'username': self.user.username, 'password': self.password, **extra}
        )

    def test_login_page_offers_passkey_sign_in(self):
        response = self.client.get(self.login_url)

        self.assertContains(response, 'id="passkey-verification-button"')
        self.assertContains(response, reverse('otp_webauthn:credential-authentication-begin'))

    def test_passkey_only_account_cannot_use_a_password(self):
        make_passkey(self.user)

        response = self.post_login()

        self.assertEqual(response.status_code, 200)
        self.assertIn('This account signs in with a passkey.', response.context['form'].non_field_errors())
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_passkey_plus_totp_still_accepts_password_and_code(self):
        make_passkey(self.user)
        device = TOTPDevice.objects.create(user=self.user, name='Authenticator', confirmed=True)

        self.assertEqual(self.post_login(otp_token=current_token(device)).status_code, 302)

    def test_unconfirmed_passkey_does_not_gate_login(self):
        make_passkey(self.user, confirmed=False)

        self.assertEqual(self.post_login().status_code, 302)

    def test_unverified_session_cannot_register_a_passkey_on_a_protected_account(self):
        TOTPDevice.objects.create(user=self.user, name='Authenticator', confirmed=True)
        self.client.force_login(self.user)

        response = self.client.post(reverse('otp_webauthn:credential-registration-begin'))

        self.assertEqual(response.status_code, 403)

    def test_unenrolled_account_can_start_passkey_registration(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse('otp_webauthn:credential-registration-begin'))

        self.assertEqual(response.status_code, 200)

    def test_registration_rejects_anonymous_requests(self):
        response = self.client.post(reverse('otp_webauthn:credential-registration-begin'))

        self.assertIn(response.status_code, (401, 403))

    def test_passkey_login_options_are_available_anonymously(self):
        response = self.client.post(reverse('otp_webauthn:credential-authentication-begin'))

        self.assertEqual(response.status_code, 200)


class AdminLoginFactorsTests(TestCase):
    def setUp(self):
        cache.clear()
        self.url = reverse('admin:login_factors')
        self.enrolled = User.objects.create_superuser('enrolled', 'e@example.com', 'pw-123456789')
        TOTPDevice.objects.create(user=self.enrolled, name='Authenticator', confirmed=True)
        self.plain = User.objects.create_superuser('plain', 'p@example.com', 'pw-123456789')
        self.keyed = User.objects.create_superuser('keyed', 'k@example.com', 'pw-123456789')
        make_passkey(self.keyed)

    def lookup(self, username):
        return self.client.post(self.url, {'username': username}).json()

    def test_enrolled_account_asks_for_a_code(self):
        self.assertEqual(self.lookup('enrolled'), {'code': True, 'passkey_only': False})

    def test_unenrolled_account_does_not(self):
        self.assertEqual(self.lookup('plain'), {'code': False, 'passkey_only': False})

    def test_passkey_only_account_is_flagged(self):
        self.assertEqual(self.lookup('keyed'), {'code': False, 'passkey_only': True})

    def test_unknown_and_non_staff_names_look_unenrolled(self):
        User.objects.create_user('visitor', password='pw-123456789')

        self.assertEqual(self.lookup('nobody'), {'code': False, 'passkey_only': False})
        self.assertEqual(self.lookup('visitor'), {'code': False, 'passkey_only': False})

    def test_get_is_refused(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_code_field_is_collapsed_until_asked_for(self):
        html = self.client.get(reverse('admin:login')).content.decode()

        self.assertIn('id="otpReveal"', html)
        self.assertNotIn('otp-reveal is-open', html)

    def test_code_field_is_open_after_a_failed_attempt(self):
        response = self.client.post(
            reverse('admin:login'), {'username': 'enrolled', 'password': 'pw-123456789'}
        )

        self.assertContains(response, 'otp-reveal is-open')


class MyAccountTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='plain_staff', email='s@example.com', password='pw-12345-xyz', is_staff=True
        )
        self.client.force_login(self.user)

    def test_staff_without_perms_can_open_and_update(self):
        url = reverse('admin:my_account')
        page = self.client.get(url)
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, reverse('admin:password_change'))

        response = self.client.post(url, {'first_name': 'Ann', 'last_name': 'Lee', 'email': 'a@example.com', 'contact': '0244'})
        self.assertRedirects(response, url)
        self.user.refresh_from_db()
        self.assertEqual((self.user.first_name, self.user.email), ('Ann', 'a@example.com'))
        self.assertEqual(self.user.user_profile.contact, '0244')

    def test_menu_links_to_account_page(self):
        page = self.client.get(reverse('admin:my_account'))
        self.assertContains(page, f'href="{reverse("admin:my_account")}" class="dropdown-item"')

    def test_staff_profile_shown_and_editable(self):
        from datetime import date

        from domains.company.hr.staff.models import Member

        member = Member.objects.create(user=self.user, started_on=date(2024, 1, 1))
        url = reverse('admin:my_account')
        page = self.client.get(url)
        self.assertContains(page, member.staff_id)

        response = self.client.post(url, {
            'first_name': 'Ann', 'last_name': 'Lee', 'email': 'a@example.com', 'contact': '',
            'member-about': 'Hi', 'member-gender': '', 'member-date_of_birth': '',
            'member-nationality': 'GH', 'member-hometown': 'Accra',
        })
        self.assertRedirects(response, url)
        member.refresh_from_db()
        self.assertEqual((member.about, member.hometown), ('Hi', 'Accra'))


class UserAdminFormTests(TestCase):
    def test_superuser_status_is_not_on_the_form(self):
        admin_user = User.objects.create_superuser('root', 'r@example.com', 'pw-12345-xyz')
        self.client.force_login(admin_user)
        page = self.client.get(reverse('admin:auth_user_change', args=[admin_user.pk]))
        self.assertEqual(page.status_code, 200)
        self.assertNotIn('is_superuser', page.context['adminform'].form.fields)
