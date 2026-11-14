from io import BytesIO

from django.contrib import admin
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase
from django.urls import NoReverseMatch, reverse
from django_otp.plugins.otp_totp.models import TOTPDevice
from PIL import Image

from common.admin import sidebar_navigation
from domains.accounts.admin import CustomUserAdmin
from domains.accounts.models import user_profile

from .helpers import current_token


class AdminPageRenderTests(TestCase):
    """Renders the admin under unfold. Tests run with DEBUG=False, so this also covers
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
            reverse('admin:website_products_product_changelist'),
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

    def test_unfold_skin_is_applied(self):
        response = self.client.get(reverse('admin:index'))

        self.assertContains(response, 'nav-sidebar-apps')
        self.assertContains(response, 'Seoto')

    def test_sidebar_uses_animated_collapse_markup(self):
        response = self.client.get(reverse('admin:index'))

        self.assertContains(response, 'sidebar-shell')
        self.assertContains(response, 'nav-collapse-inner')


class SidebarSectionTests(TestCase):
    """`sidebar_navigation` regroups the flat app list into source-tree sections."""

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_superuser('root', 'root@example.com', 'pw-pw-pw-pw')
        self.request = RequestFactory().get('/admin/')
        self.request.user = self.user

    def navigation(self):
        return {group['title']: group for group in sidebar_navigation(self.request)}

    def titles(self, group):
        return {link['title'] for item in group['items'] for link in item['items']}

    def test_sections_replace_per_app_groups(self):
        names = [group['title'] for group in sidebar_navigation(self.request)]

        self.assertEqual(names, ['Apps', 'Company', 'System', 'Website'])

    def test_models_land_in_their_section(self):
        navigation = self.navigation()

        self.assertLessEqual({'Users', 'Groups', 'TOTP devices'}, self.titles(navigation['System']))
        self.assertLessEqual({'Posts', 'Transactions', 'Meals'}, self.titles(navigation['Apps']))
        self.assertLessEqual({'Products', 'FAQs'}, self.titles(navigation['Website']))
        self.assertLessEqual({'Members', 'Positions'}, self.titles(navigation['Company']))
        self.assertLessEqual({'Error logs', 'Theme presets'}, self.titles(navigation['System']))

    def test_every_model_is_claimed_by_exactly_one_section(self):
        flat = sorted(
            model['admin_url']
            for app in admin.AdminSite.get_app_list(admin.site, self.request)
            for model in app['models']
            if model['admin_url']
        )
        grouped = sorted(
            link['link']
            for group in sidebar_navigation(self.request)
            for item in group['items']
            for link in item['items']
        )

        self.assertEqual(flat, grouped)

    def test_sections_expose_one_item_per_app(self):
        apps = [item['title'] for item in self.navigation()['Apps']['items']]

        self.assertEqual(apps, ['Blog', 'Foodie', 'Jotter', 'Rhymes', 'Spending Tracker'])

    def test_security_item_merges_otp_apps(self):
        items = {item['title']: item for item in self.navigation()['System']['items']}

        links = {link['title'] for link in items['Security']['items']}

        self.assertLessEqual({'TOTP devices', 'Static devices'}, links)
        self.assertNotIn('Authenticator Apps', items)

    def test_only_the_first_section_lacks_a_separator(self):
        separators = [group['separator'] for group in sidebar_navigation(self.request)]

        self.assertEqual(separators, [False, True, True, True])

    def test_users_without_permissions_get_no_sections(self):
        staff = User.objects.create_user('staff', 'staff@example.com', 'pw-pw-pw-pw', is_staff=True)
        self.request.user = staff

        self.assertEqual(sidebar_navigation(self.request), [])


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
