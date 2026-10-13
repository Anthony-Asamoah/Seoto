import uuid

from django.test import override_settings

from domains.consultations.models import ConsultationBooking, ConsultationRequest
from domains.consultations.serializers import ConsultationCreatedSerializer

from .helpers import ConsultationApiTestCase, full_payload, quick_payload

CALENDLY = 'https://calendly.com/test/consultation'


@override_settings(CALENDLY_URL=CALENDLY)
class CreateConsultationTests(ConsultationApiTestCase):

    def test_quick_message_is_saved_with_a_pending_booking(self):
        response = self.submit(quick_payload())

        self.assertEqual(response.status_code, 200)
        consultation = ConsultationRequest.objects.get()
        self.assertEqual(consultation.kind, 'quick')
        self.assertEqual(consultation.name, 'Kofi')
        self.assertEqual(consultation.phone, '+233 24 111 2222')
        self.assertEqual(consultation.email, '')
        self.assertEqual(consultation.booking.scheduling_url, CALENDLY)
        self.assertIsNone(consultation.booking.start_time)
        self.assertEqual(consultation.booking.event_uri, '')

    def test_full_submission_stores_every_field(self):
        response = self.submit(full_payload(), HTTP_USER_AGENT='TestBrowser/1.0')

        self.assertEqual(response.status_code, 200)
        consultation = ConsultationRequest.objects.get()
        self.assertEqual(consultation.kind, 'full')
        self.assertEqual(consultation.email, 'ama@example.com')
        self.assertEqual(consultation.company, 'Mensah Foods')
        self.assertEqual(consultation.interest, 'custom-build')
        self.assertEqual(consultation.budget, '5k-15k')
        self.assertEqual(consultation.timeline, '1-3-months')
        self.assertEqual(consultation.message, 'We need an ordering system.')
        self.assertEqual(consultation.source_ip, '127.0.0.1')
        self.assertEqual(consultation.user_agent, 'TestBrowser/1.0')
        self.assertTrue(ConsultationBooking.objects.filter(consultation=consultation).exists())

    def test_response_matches_the_frontend_contract(self):
        body = self.submit(full_payload()).json()
        consultation = ConsultationRequest.objects.get()

        self.assertEqual(body, {
            'ok': True,
            'referenceId': str(consultation.reference_id),
            'booking': {
                'provider': 'calendly',
                'schedulingUrl': CALENDLY,
                'prefill': {'name': 'Ama Mensah', 'email': 'ama@example.com'},
            },
        })
        self.assertCountEqual(body.keys(), ConsultationCreatedSerializer().fields.keys())

    def test_quick_message_prefills_a_null_email(self):
        body = self.submit(quick_payload()).json()
        self.assertIsNone(body['booking']['prefill']['email'])

    def test_strings_are_trimmed_and_empty_optionals_stored_blank(self):
        self.submit(full_payload(
            name='  Ama  ', company='   ', interest='', budget=None, timeline=None,
        ))

        consultation = ConsultationRequest.objects.get()
        self.assertEqual(consultation.name, 'Ama')
        self.assertEqual(consultation.company, '')
        self.assertEqual(consultation.interest, '')
        self.assertEqual(consultation.budget, '')
        self.assertEqual(consultation.timeline, '')

    def test_recaptcha_token_is_accepted_and_ignored(self):
        response = self.submit(full_payload(recaptchaToken='some-token'))
        self.assertEqual(response.status_code, 200)

    def test_trailing_slash_is_accepted(self):
        response = self.post_json('/v1/consultations/', quick_payload())
        self.assertEqual(response.status_code, 200)

    def test_spoofed_forwarded_ip_is_not_stored(self):
        self.submit(quick_payload(), HTTP_X_FORWARDED_FOR='not-an-ip')
        self.assertIsNone(ConsultationRequest.objects.get().source_ip)


@override_settings(CALENDLY_URL=CALENDLY)
class HoneypotTests(ConsultationApiTestCase):

    def test_filled_honeypot_returns_success_and_saves_nothing(self):
        response = self.submit(full_payload(honeypot='http://spam.example'))

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body['ok'])
        uuid.UUID(body['referenceId'])
        self.assertEqual(body['booking']['schedulingUrl'], CALENDLY)
        self.assertEqual(ConsultationRequest.objects.count(), 0)
        self.assertEqual(ConsultationBooking.objects.count(), 0)

    def test_honeypot_wins_over_validation(self):
        response = self.submit({'honeypot': 'x'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ConsultationRequest.objects.count(), 0)
