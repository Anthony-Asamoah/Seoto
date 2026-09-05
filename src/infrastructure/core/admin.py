"""Admin site wiring: a TOTP second factor on top of the stock admin login.

Imported lazily by Django (see `infrastructure.core.apps.OTPAdminConfig`), because
django_otp pulls in auth models that aren't loadable while INSTALLED_APPS is being read.
"""

from django_otp.admin import OTPAdminSite

# Sidebar sections mirroring the source tree, each holding the apps that live there:
# (section label, heading, icon, ((app label, sub-heading, icon), ...)).
# The section label becomes the pseudo-app's label, so JAZZMIN_SETTINGS['icons'] keys
# models as `<section>.<ModelName>`, not `<app_label>.<ModelName>`.
SIDEBAR_SECTIONS = (
    ('site', 'Site', 'fas fa-globe', (
        ('accounts', 'Accounts', 'fas fa-id-badge'),
        ('home', 'Home', 'fas fa-house'),
        ('pwa', 'PWA', 'fas fa-bell'),
        ('theme', 'Theme', 'fas fa-palette'),
    )),
    ('feature_apps', 'Feature Apps', 'fas fa-shapes', (
        ('blog', 'Blog', 'fas fa-newspaper'),
        ('spending_tracker', 'Spending Tracker', 'fas fa-wallet'),
        ('foodie', 'Foodie', 'fas fa-utensils'),
        ('jotter', 'Jotter', 'fas fa-list-check'),
        ('rhymes', 'Rhymes', 'fas fa-music'),
    )),
    ('company', 'Company', 'fas fa-building', (
        ('company_products', 'Products', 'fas fa-cubes'),
        ('company_faqs', 'FAQs', 'fas fa-circle-question'),
        ('company_staff', 'Staff', 'fas fa-user-tie'),
    )),
    ('security', 'Security', 'fas fa-shield-halved', (
        ('auth', 'Users & Groups', 'fas fa-users-cog'),
        ('otp_totp', 'Authenticator Apps', 'fas fa-mobile-screen'),
        ('otp_static', 'Backup Codes', 'fas fa-key'),
    )),
)


class SeotoAdminSite(OTPAdminSite):
    """Admin site that treats users without a verified OTP device as non-staff."""

    # Keep the stock instance name, otherwise every {% url 'admin:...' %} breaks.
    name = 'admin'

    # django-otp defaults to its own bare template; use ours so jazzmin still skins it.
    login_template = 'admin/login.html'

    def __init__(self, name='admin'):
        super().__init__(name)

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
            for member_label, sub_heading, sub_icon in members:
                app = remaining.pop(member_label, None)
                if not app:
                    continue
                models.extend(app['models'])
                subgroups.append({
                    'name': sub_heading,
                    'icon': sub_icon,
                    'models': app['models'],
                })
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
        return sections + list(remaining.values())
