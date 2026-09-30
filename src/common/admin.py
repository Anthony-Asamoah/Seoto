"""Admin site wiring: a TOTP second factor on top of the stock admin login.

Imported lazily by Django (see `common.apps.OTPAdminConfig`), because
django_otp pulls in auth models that aren't loadable while INSTALLED_APPS is being read.
"""

from django_otp.admin import OTPAdminAuthenticationForm, OTPAdminSite

from common.admin_forms import RecaptchaAdminLoginMixin
from domains.accounts.otp import OptionalOTPMixin


class OTPAdminLoginForm(RecaptchaAdminLoginMixin, OptionalOTPMixin, OTPAdminAuthenticationForm):
    pass


SIDEBAR_SECTIONS = (
    ('system', 'System', 'fas fa-gears', (
        ('accounts', 'Accounts', 'fas fa-id-badge'),
        ('home', 'Home', 'fas fa-house'),
        ('pwa', 'PWA', 'fas fa-bell'),
        ('theme', 'Theme', 'fas fa-palette'),
        ('auth', 'Users & Groups', 'fas fa-users-cog'),
        (('otp_totp', 'otp_static', 'django_otp_webauthn'), 'Security', 'fas fa-shield-halved'),
    )),
    ('apps', 'Apps', 'fas fa-shapes', (
        ('blog', 'Blog', 'fas fa-newspaper'),
        ('spending_tracker', 'Spending Tracker', 'fas fa-wallet'),
        ('foodie', 'Foodie', 'fas fa-utensils'),
        ('jotter', 'Jotter', 'fas fa-list-check'),
        ('rhymes', 'Rhymes', 'fas fa-music'),
    )),
    ('website', 'Website', 'fas fa-window-maximize', (
        ('website_products', 'Products', 'fas fa-cubes'),
        ('website_faqs', 'FAQs', 'fas fa-circle-question'),
    )),
    ('company', 'Company', 'fas fa-building', (
        ('company_staff', 'Staff', 'fas fa-user-tie'),
    )),
)


class SeotoAdminSite(OTPAdminSite):
    """Admin site where a user with an enrolled device must verify it; everyone else may sign in on a password."""

    # Keep the stock instance name, otherwise every {% url 'admin:...' %} breaks.
    name = 'admin'

    # django-otp defaults to its own bare template; use ours so jazzmin still skins it.
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

    def get_app_list(self, request, app_label=None):
        """Regroup the flat per-app list into the sections above.

        Each section carries a flat `models` list (what jazzmin and the dashboard read)
        plus `subgroups` holding the same model dicts split by owning app, which
        `templates/admin/base_site.html` renders as a second sidebar level. The two share
        dict identity on purpose: jazzmin deep-copies the app list and then stamps `url`
        and `icon` onto the entries in `models`, and a deepcopy preserves internal
        aliasing, so the subgroup entries pick those up for free.

        A single app's own page (`app_label` given) is left alone so its breadcrumbs and
        title stay coherent.
        """
        app_list = super().get_app_list(request, app_label)
        if app_label:
            return app_list

        remaining = {app['app_label']: app for app in app_list}
        sections = []

        for label, heading, icon, members in SIDEBAR_SECTIONS:
            models, subgroups = [], []
            for member_labels, sub_heading, sub_icon in members:
                if isinstance(member_labels, str):
                    member_labels = (member_labels,)
                sub_models = []
                for member_label in member_labels:
                    app = remaining.pop(member_label, None)
                    if app:
                        sub_models.extend(app['models'])
                if not sub_models:
                    continue
                sub_models.sort(key=lambda model: model['name'].lower())
                subgroups.append({
                    'name': sub_heading,
                    'icon': sub_icon,
                    'models': sub_models,
                })
            subgroups.sort(key=lambda group: group['name'].lower())
            for group in subgroups:
                models.extend(group['models'])
            if models:
                sections.append({
                    'name': heading,
                    'app_label': label,
                    'icon': icon,
                    # No single URL fits a merged section; the sidebar renders these as
                    # collapsible parents rather than links.
                    'app_url': '',
                    'has_module_perms': True,
                    'models': models,
                    'subgroups': subgroups,
                })

        # Anything not claimed by a section (a newly added app) keeps its own group.
        return sorted([*sections, *remaining.values()], key=lambda app: app['name'].lower())
