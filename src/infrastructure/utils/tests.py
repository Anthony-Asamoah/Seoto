from email import message_from_string, policy
from unittest import mock

from django.core import mail
from django.test import TestCase, override_settings

from infrastructure.utils import email as email_utils
from infrastructure.utils import send_branded_email


def sent():
    return mail.outbox[-1].message()


def parts(message):
    return {part.get_content_type() for part in message.walk()}


class SendBrandedEmailTests(TestCase):
    """The one place every outgoing email is assembled."""

    def send(self, **kwargs):
        defaults = {
            'subject': 'Hello',
            'template': 'emails/user_onboarding.html',
            'context': {'user': mock.Mock(first_name='Grace', username='grace',
                                          email='grace@example.com')},
            'to': ['grace@example.com'],
        }
        return send_branded_email(**{**defaults, **kwargs})

    def test_app_domain_is_always_available_to_the_template(self):
        """base_email.html's footer link renders blank without it."""
        with override_settings(APP_DOMAIN='https://example.test'):
            self.send()

        self.assertIn('https://example.test', sent().get_payload(0).get_payload(1).get_content())

    def test_caller_context_wins_over_the_defaults(self):
        with override_settings(APP_DOMAIN='https://example.test'):
            self.send(context={'user': mock.Mock(first_name='G', username='g', email='g@e.com'),
                               'app_domain': 'https://override.test'})

        self.assertIn('https://override.test', sent().get_payload(0).get_payload(1).get_content())

    def test_logo_rides_along_as_an_inline_related_part(self):
        self.send()
        message = sent()

        self.assertEqual(message.get_content_type(), 'multipart/related')
        self.assertIn('image/png', parts(message))
        logo = [p for p in message.walk() if p.get_content_type() == 'image/png'][0]
        self.assertEqual(logo.get('Content-ID'), f'<{email_utils.LOGO_CID}>')
        self.assertEqual(logo.get_content_disposition(), 'inline')

    def test_html_references_the_logo_by_cid(self):
        self.send()

        html = sent().get_payload(0).get_payload(1).get_content()
        self.assertIn(f'cid:{email_utils.LOGO_CID}', html)

    def test_serialised_message_round_trips(self):
        """Retyping the root must not corrupt the MIME framing a client has to parse."""
        self.send()
        raw = sent().as_string()

        reparsed = message_from_string(raw, policy=policy.default)

        self.assertEqual(reparsed.get_content_type(), 'multipart/related')
        self.assertIn('text/html', parts(reparsed))
        logo = [p for p in reparsed.walk() if p.get_content_type() == 'image/png'][0]
        self.assertEqual(logo.get('Content-ID'), f'<{email_utils.LOGO_CID}>')
        self.assertEqual(logo.get_content(), email_utils.LOGO_PATH.read_bytes())

    def test_text_body_defaults_to_the_stripped_html(self):
        self.send()

        text = sent().get_payload(0).get_payload(0).get_content()
        self.assertIn('Welcome', text)
        self.assertNotIn('<', text)

    def test_explicit_text_body_is_used_verbatim(self):
        self.send(text_body='plain and simple')

        self.assertEqual(sent().get_payload(0).get_payload(0).get_content().strip(),
                         'plain and simple')

    def test_a_bare_string_recipient_is_accepted(self):
        self.send(to='solo@example.com')

        self.assertEqual(mail.outbox[-1].to, ['solo@example.com'])

    def test_blank_addresses_are_dropped(self):
        self.send(to=['a@example.com', '', None])

        self.assertEqual(mail.outbox[-1].to, ['a@example.com'])

    def test_nothing_is_sent_when_no_one_is_addressable(self):
        self.assertFalse(self.send(to=['', None]))
        self.assertEqual(mail.outbox, [])

    def test_a_missing_logo_does_not_stop_the_send(self):
        with mock.patch.object(email_utils, '_logo_bytes', None), \
             mock.patch.object(email_utils, 'LOGO_PATH', email_utils.Path('/nope/missing.png')):
            self.send()

        message = sent()
        self.assertNotIn('image/png', parts(message))
        self.assertEqual(message.get_content_type(), 'multipart/alternative')
