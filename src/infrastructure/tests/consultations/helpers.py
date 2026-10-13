from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

CREATE_URL = '/v1/consultations'
RATE_LIMITED_PATHS = ('/v1/consultations', '/v1/consultations/')


def full_payload(**overrides):
    return {
        'quickMessage': False,
        'name': 'Ama Mensah',
        'email': 'ama@example.com',
        'company': 'Mensah Foods',
        'phone': '+233 50 000 0000',
        'interest': 'custom-build',
        'message': 'We need an ordering system.',
        'budget': '5k-15k',
        'timeline': '1-3-months',
        'honeypot': '',
        'recaptchaToken': None,
        **overrides,
    }


def quick_payload(**overrides):
    return {
        'quickMessage': True,
        'name': 'Kofi',
        'phone': '+233 24 111 2222',
        'message': 'Call me about a website.',
        'honeypot': '',
        **overrides,
    }


def booking_url(reference_id):
    return reverse('consultations_booking_create', kwargs={'reference_id': reference_id})


class ConsultationApiTestCase(TestCase):
    """Every test posts from 127.0.0.1, so reset its rate-limit counters."""

    def setUp(self):
        cache.delete_many([f'rate_limit:{path}:127.0.0.1' for path in RATE_LIMITED_PATHS])

    def post_json(self, url, payload, **extra):
        return self.client.post(url, payload, content_type='application/json', **extra)

    def submit(self, payload, **extra):
        return self.post_json(CREATE_URL, payload, **extra)
