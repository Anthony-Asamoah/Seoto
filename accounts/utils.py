from django.conf import settings
from django.core.mail import send_mail


def user_directory_file_path(instance, filename, prefix: str = None, suffix: str = None):
    path = f"{instance.user.username}/{filename}"
    if prefix:
        if not prefix.endswith('/'):
            prefix = '/' + prefix
            path = prefix + path
    if suffix:
        if not suffix.startswith('/'):
            suffix = '/' + suffix
            path = path + suffix
    return path


def trigger_user_onboarded_email(user_obj):
    mail_title = f'Welcome to Seoto'
    mail_body = f'''
Your account has been successfully set up with the platform.

Welcome {user_obj.first_name}!

'''
    mail_sender = settings.EMAIL_HOST_USER
    mail_recipient = [settings.EMAIL_HOST_USER]
    send_mail(mail_title, mail_body, mail_sender, mail_recipient, fail_silently=False)
