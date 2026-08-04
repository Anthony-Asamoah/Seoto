import logging
from datetime import datetime

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from infrastructure.utils import send_branded_email

from domains.home.utils import get_client_ip


@csrf_exempt
def incoming(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    ip = get_client_ip(request)
    timestamp = datetime.now().utcnow()

    try:
        send_branded_email(
            'Seoto Webhook Accessed',
            'emails/webhook_notification.html',
            {
                'timestamp': timestamp,
                'ip_address': ip,
                'request_body': request.body.decode(),
            },
            [settings.EMAIL_HOST_USER],
            text_body=f"""
Webhook was accessed on {timestamp},

By {ip}.


Body/Data:

{request.body.decode()}

~ Seoto Security Notifications
""",
        )
    except Exception:
        logging.warning('Webhook email not sent')
        return HttpResponse(status=500)
    return HttpResponse(status=200)
