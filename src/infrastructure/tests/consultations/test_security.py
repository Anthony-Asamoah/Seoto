from django.conf import settings
from django.test import Client, override_settings

from domains.consultations.models import ConsultationRequest

from .helpers import CREATE_URL, ConsultationApiTestCase, booking_url, quick_payload

ORIGIN = 'https://seoto.org'


@override_settings(CORS_ALLOWED_ORIGINS=[ORIGIN])
class CorsTests(ConsultationApiTestCase):

    def test_allowed_origin_gets_the_cors_header(self):
        response = self.submit(quick_payload(), HTTP_ORIGIN=ORIGIN)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Access-Control-Allow-Origin'], ORIGIN)

    def test_preflight_is_answered(self):
        response = self.client.options(
            CREATE_URL,
            HTTP_ORIGIN=ORIGIN,
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='POST',
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS='content-type',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Access-Control-Allow-Origin'], ORIGIN)
        self.assertIn('content-type', response.headers['Access-Control-Allow-Headers'])

    def test_booking_path_is_covered_too(self):
        response = self.client.options(
            booking_url('00000000-0000-0000-0000-000000000000'),
            HTTP_ORIGIN=ORIGIN,
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='POST',
        )
        self.assertEqual(response.headers['Access-Control-Allow-Origin'], ORIGIN)

    def test_unknown_origin_gets_no_cors_header(self):
        response = self.submit(quick_payload(), HTTP_ORIGIN='https://evil.example')
        self.assertNotIn('Access-Control-Allow-Origin', response.headers)


class RateLimitTests(ConsultationApiTestCase):

    def test_both_path_spellings_have_an_entry(self):
        for path in ('/v1/consultations', '/v1/consultations/'):
            self.assertEqual(
                settings.RATE_LIMIT_CONFIG[path], {'max_requests': 5, 'window': 300},
            )

    def test_sixth_submission_in_the_window_is_refused(self):
        for _ in range(5):
            self.assertEqual(self.submit(quick_payload()).status_code, 200)

        response = self.submit(quick_payload())

        self.assertEqual(response.status_code, 429)
        self.assertEqual(ConsultationRequest.objects.count(), 5)

    def test_trailing_slash_path_is_limited_too(self):
        for _ in range(5):
            self.post_json('/v1/consultations/', quick_payload())

        self.assertEqual(self.post_json('/v1/consultations/', quick_payload()).status_code, 429)


class CsrfTests(ConsultationApiTestCase):

    def test_post_without_a_csrf_token_is_accepted(self):
        client = Client(enforce_csrf_checks=True)

        response = client.post(CREATE_URL, quick_payload(), content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ConsultationRequest.objects.count(), 1)
