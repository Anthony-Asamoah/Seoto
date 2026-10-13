import uuid
from datetime import datetime, timezone

from domains.consultations.models import ConsultationRequest

from .helpers import ConsultationApiTestCase, booking_url, full_payload

EVENT_URI = 'https://api.calendly.com/scheduled_events/EV123'
INVITEE_URI = 'https://api.calendly.com/scheduled_events/EV123/invitees/IN456'


class BookingTests(ConsultationApiTestCase):

    def setUp(self):
        super().setUp()
        self.reference_id = self.submit(full_payload()).json()['referenceId']

    def booking(self):
        return ConsultationRequest.objects.get(reference_id=self.reference_id).booking

    def test_booking_stores_the_calendly_event(self):
        response = self.post_json(booking_url(self.reference_id), {'event': {
            'uri': EVENT_URI,
            'inviteeUri': INVITEE_URI,
            'startTime': '2026-11-02T14:30:00Z',
        }})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'ok': True})
        booking = self.booking()
        self.assertEqual(booking.event_uri, EVENT_URI)
        self.assertEqual(booking.invitee_uri, INVITEE_URI)
        self.assertEqual(booking.start_time, datetime(2026, 11, 2, 14, 30, tzinfo=timezone.utc))

    def test_frontend_shape_without_start_time(self):
        # BookingStep.tsx only forwards the two URIs.
        response = self.post_json(booking_url(self.reference_id), {
            'event': {'uri': EVENT_URI, 'inviteeUri': INVITEE_URI},
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.booking().event_uri, EVENT_URI)
        self.assertIsNone(self.booking().start_time)

    def test_path_without_trailing_slash_matches_the_frontend(self):
        url = f'/v1/consultations/{self.reference_id}/booking'
        self.assertEqual(booking_url(self.reference_id), url)
        response = self.post_json(url + '/', {'event': {'uri': EVENT_URI}})
        self.assertEqual(response.status_code, 200)

    def test_unknown_reference_is_404(self):
        response = self.post_json(booking_url(uuid.uuid4()), {'event': {'uri': EVENT_URI}})

        self.assertEqual(response.status_code, 404)
        self.assertIn('message', response.json())

    def test_non_uuid_reference_is_404(self):
        response = self.post_json('/v1/consultations/not-a-uuid/booking', {'event': {}})
        self.assertEqual(response.status_code, 404)

    def test_malformed_event_is_400(self):
        response = self.post_json(booking_url(self.reference_id), {'event': {
            'uri': 'not a url', 'startTime': 'tomorrow',
        }})

        self.assertEqual(response.status_code, 400)
        message = response.json()['message']
        self.assertIn('event.uri must be a URL.', message)
        self.assertIn('event.startTime must be an ISO 8601 datetime.', message)
        self.assertEqual(self.booking().event_uri, '')

    def test_missing_event_is_400(self):
        response = self.post_json(booking_url(self.reference_id), {})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['message'], 'event must be an object.')
