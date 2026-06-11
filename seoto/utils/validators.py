"""
Reusable form/model field validators.

Phone validation is built on Google's libphonenumber (`phonenumbers`). It
accepts full international format (e.g. ``+233244123456``) as well as national
numbers, which are interpreted against ``DEFAULT_REGION``. Use ``validate_phone``
as a field validator and ``normalize_phone`` to canonicalise input to E.164
before storing.
"""
import phonenumbers
from django.core.exceptions import ValidationError

# National-format numbers (no leading "+") are parsed against this region.
# International numbers carry their own country code and ignore it. Ghana is
# the project's home market; override per-call via the `region` argument.
DEFAULT_REGION = 'GH'

INVALID_PHONE_MESSAGE = 'Enter a valid phone number, including the country code.'


def validate_phone(value, region=DEFAULT_REGION):
    """Django validator: raise ``ValidationError`` if ``value`` isn't a valid number.

    Empty values pass (let the field's ``required`` flag own that decision).
    """
    if not value:
        return
    try:
        parsed = phonenumbers.parse(value, region)
    except phonenumbers.NumberParseException:
        raise ValidationError(INVALID_PHONE_MESSAGE, code='invalid_phone')
    if not phonenumbers.is_valid_number(parsed):
        raise ValidationError(INVALID_PHONE_MESSAGE, code='invalid_phone')


def normalize_phone(value, region=DEFAULT_REGION):
    """Return the E.164 form (e.g. ``+233244123456``) of a valid number.

    Falls back to the original value when it can't be parsed/validated, so this
    is safe to call on already-validated input or as a best-effort tidy-up.
    """
    if not value:
        return value
    try:
        parsed = phonenumbers.parse(value, region)
    except phonenumbers.NumberParseException:
        return value
    if phonenumbers.is_valid_number(parsed):
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    return value
