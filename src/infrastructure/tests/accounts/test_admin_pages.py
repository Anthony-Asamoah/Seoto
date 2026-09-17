import copy
from io import BytesIO

from django.contrib import admin
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase
from django.urls import NoReverseMatch, reverse
from django_otp.plugins.otp_totp.models import TOTPDevice
from PIL import Image

from domains.accounts.admin import CustomUserAdmin
from domains.accounts.models import user_profile

from .helpers import current_token


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

    def test_user_change_form_hides_password_hash(self):
        response = self.client.get(reverse('admin:auth_user_change', args=[self.user.pk]))

        self.assertNotContains(response, self.user.password)
        self.assertContains(response, reverse('admin:auth_user_password_change', args=[self.user.pk]))

    def test_important_dates_are_readonly_in_general_fieldset(self):
        general = dict(CustomUserAdmin(User, admin.site).fieldsets)[None]['fields']

        self.assertIn('last_login', general)
        self.assertIn('date_joined', general)
        response = self.client.get(reverse('admin:auth_user_change', args=[self.user.pk]))
        self.assertNotContains(response, 'name="date_joined')
        self.assertNotContains(response, 'name="last_login')

    def test_profile_picture_renders_preview_buttons_not_a_url(self):
        buffer = BytesIO()
        Image.new('RGB', (8, 8), 'red').save(buffer, format='PNG')
        picture = SimpleUploadedFile('avatar.png', buffer.getvalue(), content_type='image/png')
        user_profile.objects.update_or_create(user=self.user, defaults={'picture': picture})

        response = self.client.get(reverse('admin:auth_user_change', args=[self.user.pk]))

        self.assertContains(response, 'image-preview-trigger')
        self.assertContains(response, 'image-preview-upload')
        self.assertContains(response, 'image-preview-remove')
        self.assertNotContains(response, 'Currently:')

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
        self.assertLessEqual({'ErrorLog', 'ThemePreset'}, objects('site'))

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
