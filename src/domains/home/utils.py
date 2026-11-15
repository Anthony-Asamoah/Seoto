import hashlib
import hmac
import logging

from django.conf import settings
from django.http import HttpResponse

logger = logging.getLogger(__name__)


def get_client_ip(request):
	"""Client IP from the right of X-Forwarded-For, skipping the proxies we run behind.

	Each trusted proxy appends the peer it saw, so the left side is attacker-controlled.
	Chain is Cloudflare -> Traefik: Traefik appends Cloudflare's edge IP, Cloudflare appended the client.
	"""
	remote = request.META.get('REMOTE_ADDR')
	parts = [p.strip() for p in request.META.get('HTTP_X_FORWARDED_FOR', '').split(',') if p.strip()]
	hops = settings.CLIENT_IP_PROXY_HOPS
	if not parts:
		ip = remote
	else:
		ip = parts[-(hops + 1)] if len(parts) > hops else parts[-1]

	# TEMP: verify the proxy chain in prod, then delete
	logger.warning(
		'client-ip debug: resolved=%s remote=%s xff=%r cf=%r hops=%s',
		ip, remote, request.META.get('HTTP_X_FORWARDED_FOR'), request.META.get('HTTP_CF_CONNECTING_IP'), hops,
	)
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
