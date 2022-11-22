import hashlib
import hmac
import logging

from django.http import HttpResponse


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


def webhook_paystack_handler(request):
	if get_client_ip(request) not in ["52.31.139.75", "52.49.173.169", "52.214.14.220"] + ["127.0.0.1"]:
		logging.info('Invalid IP at webhook')
		return HttpResponse(status=403)
	body = request.body

	try:
		signature = request.headers['x-paystack-signature']
	except Exception as e:
		logging.info('Paystack signature not present')
	else:
		key = "".encode()  # place paystack api key here
		hash = hmac.new(key, body, hashlib.sha512).hexdigest()

		if hash != signature:
			logging.debug(f'Signatures are not equal: \n{hash}\n{key}')
			return HttpResponse(status=403)

		logging.info(f'Verified as paystack')
