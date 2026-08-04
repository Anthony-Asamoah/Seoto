from django.conf import settings
from django.urls import reverse

from infrastructure.utils import send_branded_email


def user_directory_file_path(instance, filename, prefix: str = None, suffix: str = None):
    from datetime import datetime
    parts = []
    if prefix:
        parts.append(datetime.now().strftime(prefix).strip('/'))
    parts.append(instance.user.username)
    if suffix:
        parts.append(suffix.strip('/'))
    parts.append(filename)
    return '/'.join(parts)


def trigger_user_onboarded_email(user_obj):
    app_domain = getattr(settings, 'APP_DOMAIN', 'http://localhost:8000')

    send_branded_email(
        'Welcome to Seoto',
        'emails/user_onboarding.html',
        {'user': user_obj},
        [user_obj.email],
        text_body=f'''
Your account has been successfully set up with the platform.

Welcome {user_obj.first_name}!

Visit us at: {app_domain}

~ The Seoto Team
''',
    )


def trigger_totp_setup_email(user_obj, device):
    """Mail a one-time enrolment link.

    Only the signed link travels — never the QR code or the shared secret. A mailbox that
    someone else can read must not be enough to enrol their own authenticator.
    """
    from domains.accounts.services import make_setup_token

    mail_title = 'Set up two-factor authentication - Seoto'
    app_domain = getattr(settings, 'APP_DOMAIN', 'http://localhost:8000')
    setup_url = app_domain.rstrip('/') + reverse(
        'totp_setup_confirm', kwargs={'token': make_setup_token(device)}
    )

    text_content = f'''
Hello{f' {user_obj.first_name}' if user_obj.first_name else ''},

An administrator has set up two-factor authentication for your Seoto account.

Account Details:
Username: {user_obj.username}
Email: {user_obj.email}

Open the link below to pair your authenticator app:
{setup_url}

The link expires in 24 hours and stops working once your app is paired.

SECURITY NOTE:
If you weren't expecting this, ignore the email and tell us — nothing changes until the link is opened.

Best regards,
The Seoto Team

---
This email was sent automatically. Please do not reply to this email.
'''

    send_branded_email(
        mail_title,
        'emails/totp_setup.html',
        {'user': user_obj, 'setup_url': setup_url},
        [user_obj.email],
        text_body=text_content,
    )
