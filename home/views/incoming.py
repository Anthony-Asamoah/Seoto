import logging
from datetime import datetime

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt

from home.utils import get_client_ip


@csrf_exempt
def incoming(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    ip = get_client_ip(request)
    timestamp = datetime.now().utcnow()

    mail_title = 'Seoto Webhook Accessed'

    # Render HTML template
    html_content = render_to_string('emails/webhook_notification.html', {
        'timestamp': timestamp,
        'ip_address': ip,
        'request_body': request.body.decode(),
        'app_domain': getattr(settings, 'APP_DOMAIN', 'http://localhost:8000')
    })

    # Plain text fallback
    mail_body = f"""
Webhook was accessed on {timestamp},

By {ip}.


Body/Data:

{request.body.decode()}

~ Seoto Security Notifications
	"""

    mail_sender = settings.EMAIL_HOST_USER
    mail_recipient = [settings.EMAIL_HOST_USER]

    try:
        # Create email with both HTML and plain text versions
        email = EmailMultiAlternatives(
            subject=mail_title,
            body=mail_body,
            from_email=mail_sender,
            to=mail_recipient
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
    except Exception as e:
        logging.warning('Webhook email not sent')
        return HttpResponse(status=500)
    return HttpResponse(status=200)
