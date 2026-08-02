from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


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
    mail_title = 'Welcome to Seoto'

    # Render HTML template
    html_content = render_to_string('emails/user_onboarding.html', {
        'user': user_obj,
        'app_domain': getattr(settings, 'APP_DOMAIN', 'http://localhost:8000')
    })

    # Plain text fallback
    text_content = f'''
Your account has been successfully set up with the platform.

Welcome {user_obj.first_name}!

Visit us at: {getattr(settings, 'APP_DOMAIN', 'http://localhost:8000')}

~ The Seoto Team
'''

    mail_sender = settings.EMAIL_HOST_USER
    mail_recipient = [user_obj.email]

    # Create email with both HTML and plain text versions
    email = EmailMultiAlternatives(
        subject=mail_title,
        body=text_content,
        from_email=mail_sender,
        to=mail_recipient
    )
    email.attach_alternative(html_content, "text/html")
    email.send(fail_silently=False)
