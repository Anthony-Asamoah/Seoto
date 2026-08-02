from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from domains.theme.models import UserTheme, ThemePreset


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

        subject = f'New Theme Submitted for Review: {theme.name}'
        html_message = render_to_string('emails/theme_submitted.html', {
            'theme': theme,
            'site_url': settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost:8000'
        })
        plain_message = strip_tags(html_message)

        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            staff_emails,
            html_message=html_message,
            fail_silently=True
        )

    elif notification_type in ['verified', 'rejected']:
        # Notify the theme creator
        subject = f'Theme Review: {theme.name}'
        status = 'Approved' if notification_type == 'verified' else 'Rejected'

        html_message = render_to_string('emails/theme_verified.html', {
            'theme': theme,
            'status': status,
            'user': theme.created_by,
            'site_url': settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost:8000'
        })
        plain_message = strip_tags(html_message)

        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [theme.created_by.email],
            html_message=html_message,
            fail_silently=True
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
