from django.core.exceptions import ValidationError
from django.test import TestCase

from infrastructure.core.utils.validators import normalize_phone, validate_phone
from domains.author.forms import DiscoveryCallForm


class ValidatePhoneTests(TestCase):
    def test_accepts_international_format(self):
        validate_phone('+233244123456')  # should not raise
        validate_phone('+14155552671')

    def test_accepts_national_number_in_default_region(self):
        # Ghana (DEFAULT_REGION) national number, no country code.
        validate_phone('0244123456')

    def test_empty_value_passes(self):
        # `required` ownership belongs to the field, not the validator.
        validate_phone('')
        validate_phone(None)

    def test_rejects_too_short_number(self):
        with self.assertRaises(ValidationError):
            validate_phone('12345')

    def test_rejects_non_numeric_garbage(self):
        with self.assertRaises(ValidationError):
            validate_phone('not a phone')

    def test_error_uses_invalid_phone_code(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_phone('12345')
        self.assertEqual(ctx.exception.code, 'invalid_phone')


class NormalizePhoneTests(TestCase):
    def test_national_number_becomes_e164(self):
        self.assertEqual(normalize_phone('0244123456'), '+233244123456')

    def test_international_number_preserved(self):
        self.assertEqual(normalize_phone('+14155552671'), '+14155552671')

    def test_invalid_value_returned_unchanged(self):
        self.assertEqual(normalize_phone('not a phone'), 'not a phone')

    def test_empty_value_returned_unchanged(self):
        self.assertEqual(normalize_phone(''), '')


class DiscoveryCallFormPhoneTests(TestCase):
    def _data(self, **overrides):
        data = {
            'name': 'Ada Lovelace',
            'email': 'ada@example.com',
            'message': 'I would like to discuss a project.',
            'interest': 'custom',
        }
        data.update(overrides)
        return data

    def test_blank_phone_is_allowed(self):
        form = DiscoveryCallForm(data=self._data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_valid_phone_is_normalized_to_e164(self):
        form = DiscoveryCallForm(data=self._data(phone='0244123456'))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['phone'], '+233244123456')

    def test_invalid_phone_is_rejected(self):
        form = DiscoveryCallForm(data=self._data(phone='12345'))
        self.assertFalse(form.is_valid())
        self.assertIn('phone', form.errors)

    def test_full_mode_requires_email(self):
        # Default (discovery) mode can't proceed to Calendly without an email.
        data = self._data()
        data.pop('email')
        form = DiscoveryCallForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)


class DiscoveryCallFormQuickModeTests(TestCase):
    """The no-email 'quick message' path: name + phone + message, call back."""

    def _quick_data(self, **overrides):
        data = {
            'name': 'Kofi Mensah',
            'message': 'Please call me about a shop website.',
            'quick_message': '1',
            'phone': '0244123456',
        }
        data.update(overrides)
        return data

    def test_valid_without_email_or_interest(self):
        form = DiscoveryCallForm(data=self._quick_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_requires_phone(self):
        data = self._quick_data()
        data.pop('phone')
        form = DiscoveryCallForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('phone', form.errors)

    def test_save_composes_call_back_message(self):
        form = DiscoveryCallForm(data=self._quick_data())
        self.assertTrue(form.is_valid(), form.errors)
        instance = form.save(commit=False)
        self.assertEqual(instance.email, '')
        self.assertIn('call back', instance.subject.lower())
        self.assertIn('+233244123456', instance.message)
        self.assertIn('Please call me', instance.message)
