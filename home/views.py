import hashlib
import hmac
import logging
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail
from django.http import HttpResponse
from django.shortcuts import render
from datetime import datetime


def index(request):
    today = datetime.now()

    context = {
        'year': today.year
    }
    return render(request, 'Home/index.html', context)


def error404(request, exception):
    return render(request, 'Home/404.html', status=404)


def error500(request):
    return render(request, 'Home/500.html', status=500)


def get_client_ip(request):
    try:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
    except Exception as e:
        ip = request.META.get('REMOTE_ADDR')

    logging.info(f'IP: {ip}')
    return ip


@csrf_exempt
def incoming(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    if get_client_ip(request) not in ["52.31.139.75", "52.49.173.169", "52.214.14.220"] + ["127.0.0.1"]:
        logging.info('Invalid IP at webhook')
        return HttpResponse(status=403)
    body = request.body

    try:
        signature = request.headers['x-paystack-signature']
    except Exception as e:
        logging.info('Paystack signature not present')
    else:
        key = "sk_test_c3a181aef6c710d5dafe7aae359aa67028185dc8".encode()
        hash = hmac.new(key, body, hashlib.sha512).hexdigest()
        if hash != signature:
            logging.debug(f'Signatures are not equal: \n{hash}\n{key}')
            return HttpResponse(status=403)
        logging.debug(f'Verified as paystack')

    try:
        send_mail(
            f'Webhook was accessed on {datetime.now().utcnow()}',
            f'{body.decode()}.',
            'anthonyasamoah48@gmail.com',
            ['anthonyasamoah48@gmail.com'],
            fail_silently=False,
        )
    except Exception as e:
        logging.warning('Webhook email not sent')
    return HttpResponse(status=200)
