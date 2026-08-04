import copy
from io import StringIO
from unittest import mock

from django.contrib import admin
from django.contrib.auth.models import User
from django.core import mail
from django.core.cache import cache
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import RequestFactory, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import NoReverseMatch, reverse
from django_otp.oath import TOTP
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice

from domains.accounts import services


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


class AdminPageRenderTests(TestCase):
    """Renders the admin under jazzmin. Tests run with DEBUG=False, so this also covers
    the staticfiles manifest lookups that only bite once hashing is on."""

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_superuser('root', 'root@example.com', 'pw-pw-pw-pw')
        self.device = TOTPDevice.objects.create(user=self.user, name='Authenticator', confirmed=True)
        self.client.post(
            reverse('admin:login'),
            {'username': 'root', 'password': 'pw-pw-pw-pw', 'otp_token': current_token(self.device)},
        )

    def test_admin_pages_render(self):
        urls = [
            reverse('admin:index'),
            reverse('admin:auth_user_changelist'),
            reverse('admin:auth_user_change', args=[self.user.pk]),
            reverse('admin:auth_user_add'),
            reverse('admin:otp_totp_totpdevice_changelist'),
            reverse('admin:otp_totp_totpdevice_change', args=[self.device.pk]),
            reverse('admin:otp_totp_totpdevice_config', kwargs={'pk': self.device.pk}),
            reverse('admin:otp_static_staticdevice_changelist'),
            reverse('admin:blog_post_add'),
            reverse('admin:spending_tracker_transaction_changelist'),
            reverse('admin:company_products_product_changelist'),
            reverse('admin:password_change'),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_jazzmin_skin_is_applied(self):
        response = self.client.get(reverse('admin:index'))

        self.assertContains(response, 'jazzy-sidebar')
        self.assertContains(response, 'Seoto')


class SidebarSectionTests(TestCase):
    """`SeotoAdminSite.get_app_list` regroups the flat app list into source-tree sections."""

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_superuser('root', 'root@example.com', 'pw-pw-pw-pw')
        self.request = RequestFactory().get('/admin/')
        self.request.user = self.user

    def app_list(self):
        return admin.site.get_app_list(self.request)

    def test_sections_replace_per_app_groups(self):
        names = [app['name'] for app in self.app_list()]

        self.assertEqual(names, ['Site', 'Feature Apps', 'Company', 'Security'])

    def test_models_land_in_their_section(self):
        sections = {app['app_label']: app for app in self.app_list()}

        def objects(label):
            return {model['object_name'] for model in sections[label]['models']}

        self.assertLessEqual({'User', 'Group', 'TOTPDevice'}, objects('security'))
        self.assertLessEqual({'Post', 'Transaction', 'meal'}, objects('feature_apps'))
        self.assertLessEqual({'Product', 'FAQ'}, objects('company'))
        self.assertLessEqual({'Intro', 'ErrorLog'}, objects('site'))

    def test_every_model_is_claimed_by_exactly_one_section(self):
        flat = [
            (app['app_label'], model['object_name'])
            for app in admin.AdminSite.get_app_list(admin.site, self.request)
            for model in app['models']
        ]
        grouped = [
            model['object_name'] for app in self.app_list() for model in app['models']
        ]

        self.assertEqual(len(flat), len(grouped))
        self.assertEqual(sorted(name for _, name in flat), sorted(grouped))

    def test_sections_expose_subgroups_per_app(self):
        sections = {app['app_label']: app for app in self.app_list()}

        feature_apps = [group['name'] for group in sections['feature_apps']['subgroups']]

        self.assertEqual(feature_apps, ['Blog', 'Spending Tracker', 'Foodie', 'Jotter', 'Rhymes'])

    def test_subgroup_models_are_the_same_objects_as_the_flat_list(self):
        """The sidebar relies on this: jazzmin stamps `url`/`icon` onto the flat list
        only, and the subgroups pick them up through shared dict identity."""
        section = next(app for app in self.app_list() if app['app_label'] == 'company')
        flat = {id(model) for model in section['models']}
        nested = {id(model) for group in section['subgroups'] for model in group['models']}

        self.assertEqual(flat, nested)

    def test_subgroups_survive_a_deepcopy_with_identity_intact(self):
        """jazzmin deep-copies the app list before mutating it; aliasing must hold."""
        section = copy.deepcopy(
            next(app for app in self.app_list() if app['app_label'] == 'company')
        )
        for model in section['models']:
            model['url'] = 'stamped'

        nested = [model.get('url') for group in section['subgroups'] for model in group['models']]

        self.assertTrue(nested and all(url == 'stamped' for url in nested))

    def test_single_app_view_is_left_ungrouped(self):
        """The per-app page needs the real app so its breadcrumbs and title stay right."""
        app_list = admin.site.get_app_list(self.request, app_label='blog')

        self.assertEqual([app['app_label'] for app in app_list], ['blog'])


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


class UserProfileInlineTests(TestCase):
    """The profile is edited on the user's own page and has no menu entry of its own."""

    def setUp(self):
        cache.clear()
        self.admin = User.objects.create_superuser('root', 'root@example.com', 'pw-pw-pw-pw')
        device = TOTPDevice.objects.create(user=self.admin, name='Authenticator', confirmed=True)
        self.client.post(
            reverse('admin:login'),
            {'username': 'root', 'password': 'pw-pw-pw-pw', 'otp_token': current_token(device)},
        )

    def test_change_page_carries_the_profile_fields(self):
        response = self.client.get(reverse('admin:auth_user_change', args=[self.admin.pk]))

        self.assertContains(response, 'user_profile-0-contact')
        self.assertContains(response, 'user_profile-0-picture')

    def test_add_page_omits_the_inline(self):
        """The profile's FK points at a user the add form has not created yet."""
        response = self.client.get(reverse('admin:auth_user_add'))

        self.assertNotContains(response, 'user_profile-0-contact')

    def test_profile_has_no_admin_page_of_its_own(self):
        with self.assertRaises(NoReverseMatch):
            reverse('admin:accounts_user_profile_changelist')

    def test_profile_is_absent_from_the_sidebar(self):
        request = RequestFactory().get('/admin/')
        request.user = self.admin

        objects = {
            model['object_name']
            for app in admin.site.get_app_list(request)
            for model in app['models']
        }

        self.assertNotIn('user_profile', objects)
