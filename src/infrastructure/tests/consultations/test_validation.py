from domains.consultations.models import ConsultationRequest

from .helpers import ConsultationApiTestCase, full_payload, quick_payload


class ValidationTests(ConsultationApiTestCase):

    def assertRejected(self, payload, message):
        response = self.submit(payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn(message, response.json()['message'])
        self.assertEqual(ConsultationRequest.objects.count(), 0)

    def test_name_is_required(self):
        self.assertRejected(full_payload(name='   '), 'Please tell us your name.')

    def test_message_is_required_in_full_mode(self):
        self.assertRejected(full_payload(message=''), 'Let us know what you’re trying to solve.')

    def test_message_is_required_in_quick_mode(self):
        self.assertRejected(quick_payload(message=None), 'Please add a short message.')

    def test_full_mode_requires_email(self):
        self.assertRejected(full_payload(email=None), 'We need an email to reply.')

    def test_full_mode_rejects_a_malformed_email(self):
        self.assertRejected(full_payload(email='ama@'), 'That doesn’t look like a valid email.')

    def test_quick_mode_requires_phone(self):
        self.assertRejected(quick_payload(phone=''), 'Add a phone number so we can reach you.')

    def test_quick_mode_does_not_require_email(self):
        self.assertEqual(self.submit(quick_payload(email=None)).status_code, 200)

    def test_every_broken_rule_is_reported(self):
        response = self.submit(full_payload(name='', email='', message=''))
        message = response.json()['message']
        for expected in ('name', 'solve', 'email'):
            self.assertIn(expected, message)

    def test_unknown_choice_values_are_rejected(self):
        self.assertRejected(full_payload(interest='free-stuff'), "'free-stuff' is not a valid interest.")
        self.assertRejected(full_payload(budget='1m'), "'1m' is not a valid budget.")
        self.assertRejected(full_payload(timeline='never'), "'never' is not a valid timeline.")

    def test_overlong_fields_are_rejected(self):
        self.assertRejected(full_payload(name='a' * 121), 'Name must be at most 120 characters.')
        self.assertRejected(full_payload(message='a' * 5001), 'Message must be at most 5000 characters.')

    def test_non_string_values_are_rejected(self):
        self.assertRejected(full_payload(name=42), 'name must be a string.')

    def test_quick_message_flag_must_be_boolean(self):
        self.assertRejected(full_payload(quickMessage='yes'), 'quickMessage must be true or false.')

    def test_body_must_be_a_json_object(self):
        response = self.submit(['not', 'an', 'object'])
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['message'], 'Request body must be a JSON object.')

    def test_malformed_json_is_a_400_with_message(self):
        response = self.client.post(
            '/v1/consultations', '{"name": ', content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['message'], 'Request body must be valid JSON.')
