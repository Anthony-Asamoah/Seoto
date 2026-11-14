"""Admin site wiring: the Unfold skin and a TOTP second factor on top of the stock admin login.

Imported lazily by Django (see `common.apps.OTPAdminConfig`), because
django_otp pulls in auth models that aren't loadable while INSTALLED_APPS is being read.
"""

from django_otp.admin import OTPAdminAuthenticationForm, OTPAdminSite
from unfold.forms import AuthenticationForm as UnfoldAuthenticationForm
from unfold.sites import UnfoldAdminSite
from unfold.widgets import BASE_INPUT_CLASSES

from common.admin_forms import RecaptchaAdminLoginMixin
from domains.accounts.otp import OptionalOTPMixin


class OTPAdminLoginForm(
    RecaptchaAdminLoginMixin, OptionalOTPMixin, OTPAdminAuthenticationForm, UnfoldAuthenticationForm
):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        token = self.fields['otp_token']
        token.label = 'Authentication code'
        token.help_text = 'The 6-digit code from your authenticator app, or a backup code.'
        token.widget.attrs.update({
            'class': ' '.join(BASE_INPUT_CLASSES),
            'inputmode': 'numeric',
            'autocomplete': 'one-time-code',
            'spellcheck': 'false',
        })


SIDEBAR_SECTIONS = (
    ('System', (
        ('accounts', 'Accounts', 'badge'),
        ('home', 'Home', 'home'),
        ('pwa', 'PWA', 'notifications'),
        ('theme', 'Theme', 'palette'),
        ('auth', 'Users & Groups', 'manage_accounts'),
        (('otp_totp', 'otp_static', 'django_otp_webauthn'), 'Security', 'shield'),
    )),
    ('Apps', (
        ('blog', 'Blog', 'article'),
        ('spending_tracker', 'Spending Tracker', 'account_balance_wallet'),
        ('foodie', 'Foodie', 'restaurant'),
        ('jotter', 'Jotter', 'checklist'),
        ('rhymes', 'Rhymes', 'music_note'),
    )),
    ('Website', (
        ('website_products', 'Products', 'inventory_2'),
        ('website_faqs', 'FAQs', 'help'),
        ('consultations', 'Consultations', 'forum'),
    )),
    ('Company', (
        ('company_staff', 'Staff', 'groups'),
    )),
)


def _model_links(models):
    return [{'title': model['name'], 'link': model['admin_url']} for model in models if model['admin_url']]


def sidebar_navigation(request):
    """Unfold nav: section → app → models, built from the permission-filtered app list."""
    from django.contrib import admin

    remaining = {app['app_label']: app for app in admin.site.get_app_list(request)}
    groups = []

    for heading, members in SIDEBAR_SECTIONS:
        items = []
        for member_labels, title, icon in members:
            if isinstance(member_labels, str):
                member_labels = (member_labels,)
            models = [
                model
                for label in member_labels
                for model in remaining.pop(label, {'models': []})['models']
            ]
            links = _model_links(sorted(models, key=lambda model: model['name'].lower()))
            if links:
                items.append({'title': title, 'icon': icon, 'link': '#', 'items': links})
        if items:
            items.sort(key=lambda item: item['title'].lower())
            groups.append({'title': heading, 'items': items})

    # Anything not claimed by a section (a newly added app) keeps its own group.
    for app in remaining.values():
        links = _model_links(app['models'])
        if links:
            groups.append({'title': app['name'], 'items': links})

    groups.sort(key=lambda group: group['title'].lower())
    return [{**group, 'separator': index > 0, 'collapsible': True} for index, group in enumerate(groups)]


class SeotoAdminSite(UnfoldAdminSite, OTPAdminSite):
    """Admin site where a user with an enrolled device must verify it; everyone else may sign in on a password."""

    # Keep the stock instance name, otherwise every {% url 'admin:...' %} breaks.
    name = 'admin'

    # django-otp defaults to its own bare template; use ours so Unfold still skins it.
    login_template = 'admin/login.html'

    login_form = OTPAdminLoginForm

    def __init__(self, name='admin'):
        super().__init__(name)

    def get_urls(self):
        from django.urls import path

        return [
            path('login/factors/', self.login_factors, name='login_factors'),
            path('account/', self.admin_view(self.my_account), name='my_account'),
        ] + super().get_urls()

    def my_account(self, request):
        from domains.accounts.admin_views import my_account

        return my_account(request, self)

    def login_factors(self, request):
        from domains.accounts.otp import login_factors_response

        return login_factors_response(request, staff_only=True)

    def has_permission(self, request):
        from domains.accounts.services import requires_second_factor

        user = request.user
        if not (user.is_active and user.is_staff):
            return False
        return user.is_verified() or not requires_second_factor(user)
