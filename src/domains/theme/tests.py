from django.contrib.auth.models import AnonymousUser, User
from django.test import RequestFactory, TestCase, override_settings

from domains.theme.context_processors import theme_css
from domains.theme.models import UserTheme

DEFAULT_PRIMARY = '#007bff'
DEFAULT_CARD_BG = '#ffffff'


@override_settings(IS_THEME_ENABLED=True)
class ThemeCssContextProcessorTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _request(self, user):
        request = self.factory.get('/')
        request.user = user
        return request

    @override_settings(IS_THEME_ENABLED=False)
    def test_disabled_flag_returns_empty_css(self):
        context = theme_css(self._request(AnonymousUser()))

        self.assertEqual(context['user_theme_css'], '')
        self.assertEqual(context['theme_colors'], {})
        self.assertFalse(context['IS_THEME_ENABLED'])

    def test_anonymous_user_gets_defaults(self):
        context = theme_css(self._request(AnonymousUser()))

        self.assertTrue(context['IS_THEME_ENABLED'])
        self.assertEqual(context['theme_colors']['primary_color'], DEFAULT_PRIMARY)
        self.assertEqual(context['theme_colors']['card_bg_color'], DEFAULT_CARD_BG)

    def test_authenticated_user_without_theme_gets_defaults(self):
        user = User.objects.create_user(username='no_theme', password='pw')

        context = theme_css(self._request(user))

        self.assertEqual(context['theme_colors']['primary_color'], DEFAULT_PRIMARY)
        self.assertEqual(context['theme_colors']['card_bg_color'], DEFAULT_CARD_BG)

    def test_authenticated_user_theme_colors_are_used(self):
        user = User.objects.create_user(username='themed', password='pw')
        UserTheme.objects.create(
            user=user,
            is_using_preset=False,
            custom_primary_color='#ff0000',
            custom_card_bg_color='#101010',
        )

        context = theme_css(self._request(user))

        self.assertEqual(context['theme_colors']['primary_color'], '#ff0000')
        self.assertEqual(context['theme_colors']['card_bg_color'], '#101010')
        self.assertIn('--theme-primary: #ff0000;', context['user_theme_css'])
        self.assertIn('--theme-card-bg: #101010;', context['user_theme_css'])

    def test_css_is_a_style_block_of_variables(self):
        context = theme_css(self._request(AnonymousUser()))

        self.assertIn('<style>', context['user_theme_css'])
        self.assertIn('</style>', context['user_theme_css'])
        self.assertIn(f'--theme-primary: {DEFAULT_PRIMARY};', context['user_theme_css'])
