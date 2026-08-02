from django.conf import settings

from .models import UserTheme


def theme_css(request):
    """
    Context processor to inject CSS variables for the user's theme.
    This makes the theme available in all templates.
    """
    # Check if theme feature is enabled
    if not settings.IS_THEME_ENABLED:
        # Return empty CSS - let Bootstrap defaults apply
        return {
            'user_theme_css': '',
            'theme_colors': {},
            'IS_THEME_ENABLED': False
        }

    if request.user.is_authenticated:
        try:
            user_theme = UserTheme.objects.get(user=request.user)
            colors = user_theme.get_colors()
        except UserTheme.DoesNotExist:
            # Use default colors if user theme doesn't exist
            colors = {
                'primary_color': '#007bff',
                'secondary_color': '#6c757d',
                'background_color': '#ffffff',
                'text_color': '#212529',
                'text_head_color': '#000000',
                'navbar_bg': '#f8f9fa',
                'navbar_text': '#000000',
                'btn_success_bg': '#28a745',
                'btn_success_text': '#ffffff',
                'btn_danger_bg': '#dc3545',
                'btn_danger_text': '#ffffff',
                'btn_warning_bg': '#ffc107',
                'btn_warning_text': '#000000',
                'btn_info_bg': '#17a2b8',
                'btn_info_text': '#ffffff',
                'card_bg_color': '#ffffff',
                'card_header_bg_color': '#f8f9fa',
                'card_text_color': '#212529',
            }
    else:
        # Default colors for anonymous users
        colors = {
            'primary_color': '#007bff',
            'secondary_color': '#6c757d',
            'background_color': '#ffffff',
            'text_color': '#212529',
            'text_head_color': '#000000',
            'navbar_bg': '#f8f9fa',
            'navbar_text': '#000000',
            'btn_success_bg': '#28a745',
            'btn_success_text': '#ffffff',
            'btn_danger_bg': '#dc3545',
            'btn_danger_text': '#ffffff',
            'btn_warning_bg': '#ffc107',
            'btn_warning_text': '#000000',
            'btn_info_bg': '#17a2b8',
            'btn_info_text': '#ffffff',
            'card_bg_color': '#ffffff',
            'card_header_bg_color': '#f8f9fa',
            'card_text_color': '#212529',
        }

    # Generate CSS variables string
    css_variables = f"""
    <style>
        :root {{
            --theme-primary: {colors['primary_color']};
            --theme-secondary: {colors['secondary_color']};
            --theme-background: {colors['background_color']};
            --theme-text: {colors['text_color']};
            --theme-text-head: {colors['text_head_color']};
            --theme-navbar-bg: {colors['navbar_bg']};
            --theme-navbar-text: {colors['navbar_text']};
            --theme-btn-success-bg: {colors['btn_success_bg']};
            --theme-btn-success-text: {colors['btn_success_text']};
            --theme-btn-danger-bg: {colors['btn_danger_bg']};
            --theme-btn-danger-text: {colors['btn_danger_text']};
            --theme-btn-warning-bg: {colors['btn_warning_bg']};
            --theme-btn-warning-text: {colors['btn_warning_text']};
            --theme-btn-info-bg: {colors['btn_info_bg']};
            --theme-btn-info-text: {colors['btn_info_text']};
            --theme-card-bg: {colors['card_bg_color']};
            --theme-card-header-bg: {colors['card_header_bg_color']};
            --theme-card-text: {colors['card_text_color']};
        }}

        /* Apply theme colors to Bootstrap and custom elements */
        body {{
            background-color: var(--theme-background);
            color: var(--theme-text);
        }}

        /* Headers and labels use text_head_color */
        h1, h2, h3, h4, h5, h6 {{
            color: var(--theme-text-head);
        }}

        label, .form-label {{
            color: var(--theme-text-head);
        }}

        /* Help text and small text use text_color */
        .form-text, small, .text-muted {{
            color: var(--theme-text) !important;
            opacity: 0.7;
        }}

        /* Navbar */
        .navbar {{
            background-color: var(--theme-navbar-bg) !important;
        }}

        .navbar .navbar-brand,
        .navbar .nav-link,
        .navbar .btn {{
            color: var(--theme-navbar-text) !important;
        }}

        /* Primary and Secondary buttons */
        .btn-primary {{
            background-color: var(--theme-primary);
            border-color: var(--theme-primary);
            color: #ffffff;
        }}

        .btn-primary:hover, .btn-primary:focus {{
            background-color: var(--theme-primary);
            border-color: var(--theme-primary);
            filter: brightness(0.9);
        }}

        .btn-secondary {{
            background-color: var(--theme-secondary);
            border-color: var(--theme-secondary);
            color: #ffffff;
        }}

        .btn-secondary:hover, .btn-secondary:focus {{
            background-color: var(--theme-secondary);
            border-color: var(--theme-secondary);
            filter: brightness(0.9);
        }}

        /* Success buttons and alerts */
        .btn-success {{
            background-color: var(--theme-btn-success-bg) !important;
            border-color: var(--theme-btn-success-bg) !important;
            color: var(--theme-btn-success-text) !important;
        }}

        .btn-success:hover, .btn-success:focus {{
            background-color: var(--theme-btn-success-bg) !important;
            border-color: var(--theme-btn-success-bg) !important;
            filter: brightness(0.9);
        }}

        .alert-success {{
            background-color: var(--theme-btn-success-bg);
            color: var(--theme-btn-success-text);
            border-color: var(--theme-btn-success-bg);
        }}

        /* Danger buttons and alerts */
        .btn-danger {{
            background-color: var(--theme-btn-danger-bg) !important;
            border-color: var(--theme-btn-danger-bg) !important;
            color: var(--theme-btn-danger-text) !important;
        }}

        .btn-danger:hover, .btn-danger:focus {{
            background-color: var(--theme-btn-danger-bg) !important;
            border-color: var(--theme-btn-danger-bg) !important;
            filter: brightness(0.9);
        }}

        .alert-danger {{
            background-color: var(--theme-btn-danger-bg);
            color: var(--theme-btn-danger-text);
            border-color: var(--theme-btn-danger-bg);
        }}

        /* Warning buttons and alerts */
        .btn-warning {{
            background-color: var(--theme-btn-warning-bg) !important;
            border-color: var(--theme-btn-warning-bg) !important;
            color: var(--theme-btn-warning-text) !important;
        }}

        .btn-warning:hover, .btn-warning:focus {{
            background-color: var(--theme-btn-warning-bg) !important;
            border-color: var(--theme-btn-warning-bg) !important;
            filter: brightness(0.9);
        }}

        .alert-warning {{
            background-color: var(--theme-btn-warning-bg);
            color: var(--theme-btn-warning-text);
            border-color: var(--theme-btn-warning-bg);
        }}

        /* Info buttons and alerts */
        .btn-info {{
            background-color: var(--theme-btn-info-bg) !important;
            border-color: var(--theme-btn-info-bg) !important;
            color: var(--theme-btn-info-text) !important;
        }}

        .btn-info:hover, .btn-info:focus {{
            background-color: var(--theme-btn-info-bg) !important;
            border-color: var(--theme-btn-info-bg) !important;
            filter: brightness(0.9);
        }}

        .alert-info {{
            background-color: var(--theme-btn-info-bg);
            color: var(--theme-btn-info-text);
            border-color: var(--theme-btn-info-bg);
        }}

        /* Cards */
        .card {{
            background-color: var(--theme-card-bg);
            color: var(--theme-card-text);
        }}

        .card-body {{
            color: var(--theme-card-text);
        }}

        .card-header {{
            background-color: var(--theme-card-header-bg);
            color: var(--theme-text-head);
        }}

        .card-title {{
            color: var(--theme-text-head);
        }}

        /* Links */
        a {{
            color: var(--theme-primary);
        }}

        a:hover {{
            color: var(--theme-primary);
            filter: brightness(0.8);
        }}

        /* Badges */
        .badge.bg-primary {{
            background-color: var(--theme-primary) !important;
        }}

        .badge.bg-success {{
            background-color: var(--theme-btn-success-bg) !important;
        }}

        .badge.bg-danger {{
            background-color: var(--theme-btn-danger-bg) !important;
        }}

        .badge.bg-warning {{
            background-color: var(--theme-btn-warning-bg) !important;
            color: var(--theme-btn-warning-text) !important;
        }}

        .badge.bg-info {{
            background-color: var(--theme-btn-info-bg) !important;
        }}
    </style>
    """

    return {
        'user_theme_css': css_variables,
        'theme_colors': colors,
        'IS_THEME_ENABLED': True
    }
