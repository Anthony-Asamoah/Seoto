import logging
from datetime import datetime

from django.core.mail import send_mail
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from home.utils import get_client_ip


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


@csrf_exempt
def incoming(request):
	if request.method != 'POST':
		return HttpResponse(status=405)
	ip = get_client_ip(request)

	mail_title = 'Seoto Webhook Accessed'
	mail_body = f"""
Webhook was accessed on {datetime.now().utcnow()},
	
By {ip}.
	
	
Body/Data:
	
{request.body.decode()}
	
~ Seoto
	"""
	mail_sender = 'anthonyasamoah48@gmail.com'
	mail_recipient = ['anthonyasamoah48@gmail.com', ]
	try:
		send_mail(mail_title, mail_body, mail_sender, mail_recipient, fail_silently=False)
	except Exception as e:
		logging.warning('Webhook email not sent')
		return HttpResponse(status=500)
	return HttpResponse(status=200)
