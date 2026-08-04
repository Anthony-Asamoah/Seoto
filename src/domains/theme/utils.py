from django.conf import settings

from infrastructure.utils import send_branded_email

from domains.theme.models import UserTheme, ThemePreset


def _theme_colors(theme):
    return [
        ('Primary', theme.primary_color),
        ('Secondary', theme.secondary_color),
        ('Background', theme.background_color),
        ('Text', theme.text_color),
        ('Navbar BG', theme.navbar_bg),
        ('Navbar Text', theme.navbar_text),
    ]


def send_theme_notification(theme, notification_type, user_email=None):
    """
    Send email notifications for theme events.

    notification_type can be:
    - 'submitted': Notify admins when theme is submitted
    - 'verified': Notify user when theme is verified
    - 'rejected': Notify user when theme is rejected
    """
    if notification_type == 'submitted':
        # Notify all staff users
        from django.contrib.auth.models import User
        staff_emails = User.objects.filter(is_staff=True).values_list('email', flat=True)

        send_branded_email(
            f'New Theme Submitted for Review: {theme.name}',
            'emails/theme_submitted.html',
            {'theme': theme, 'theme_colors': _theme_colors(theme)},
            list(staff_emails),
            fail_silently=True,
        )

    elif notification_type in ['verified', 'rejected']:
        # Notify the theme creator
        send_branded_email(
            f'Theme Review: {theme.name}',
            'emails/theme_verified.html',
            {
                'theme': theme,
                'status': 'Approved' if notification_type == 'verified' else 'Rejected',
                'user': theme.created_by,
            },
            [theme.created_by.email],
            fail_silently=True,
        )


def get_or_create_user_theme(user):
    """Get or create UserTheme for the given user"""
    user_theme, created = UserTheme.objects.get_or_create(
        user=user,
        defaults={
            'is_using_preset': True,
            'active_preset': ThemePreset.objects.filter(is_official=True).first()
        }
    )
    return user_theme
