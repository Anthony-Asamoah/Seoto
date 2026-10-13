from datetime import timezone as dt_timezone

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator, URLValidator, validate_ipv46_address
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import (
    Budget,
    ConsultationBooking,
    ConsultationKind,
    ConsultationRequest,
    Interest,
    Timeline,
)

# Payload key -> model field, for the optional free-text fields.
OPTIONAL_TEXT_FIELDS = {'email': 'email', 'company': 'company', 'phone': 'phone'}
CHOICE_FIELDS = {'interest': Interest, 'budget': Budget, 'timeline': Timeline}

_validate_email = EmailValidator()
_validate_url = URLValidator(schemes=('http', 'https'))


class ConsultationError(ValueError):
    """Input the visitor got wrong; the API turns this into a 400."""


def honeypot_tripped(data):
    """The hidden field is only ever filled by bots."""
    value = data.get('honeypot')
    return bool(value.strip() if isinstance(value, str) else value)


def decoy_consultation(data):
    """An unsaved stand-in, so a bot's response is indistinguishable from a real one."""
    name = data.get('name')
    return ConsultationRequest(name=name.strip() if isinstance(name, str) else '')


def create_consultation(data, *, ip=None, user_agent=''):
    """Validate a reach-out submission and save it with its pending booking.

    Raises ``ConsultationError`` naming every rule the submission broke.
    """
    fields = _clean_submission(data)

    with transaction.atomic():
        consultation = ConsultationRequest.objects.create(
            **fields,
            source_ip=_clean_ip(ip),
            user_agent=(user_agent or '')[:300],
        )
        ConsultationBooking.objects.create(
            consultation=consultation, scheduling_url=settings.CALENDLY_URL,
        )
    return consultation


def record_booking(reference_id, event):
    """Store the Calendly event for a request.

    Raises ``ConsultationBooking.DoesNotExist`` for an unknown ``reference_id``
    and ``ConsultationError`` for a malformed event.
    """
    booking = ConsultationBooking.objects.select_related('consultation').get(
        consultation__reference_id=reference_id,
    )
    if not isinstance(event, dict):
        raise ConsultationError('event must be an object.')

    updates = {}
    errors = []
    for key, field in (('uri', 'event_uri'), ('inviteeUri', 'invitee_uri')):
        try:
            value = _text(event, key)
        except ConsultationError as error:
            errors.append(str(error))
            continue
        if not value:
            continue
        try:
            _validate_url(value)
        except ValidationError:
            errors.append(f'event.{key} must be a URL.')
            continue
        if len(value) > ConsultationBooking._meta.get_field(field).max_length:
            errors.append(f'event.{key} is too long.')
            continue
        updates[field] = value

    raw_start = event.get('startTime')
    if raw_start not in (None, ''):
        start_time = parse_datetime(raw_start) if isinstance(raw_start, str) else None
        if start_time is None:
            errors.append('event.startTime must be an ISO 8601 datetime.')
        else:
            if timezone.is_naive(start_time):
                start_time = timezone.make_aware(start_time, dt_timezone.utc)
            updates['start_time'] = start_time

    if errors:
        raise ConsultationError(' '.join(errors))

    for field, value in updates.items():
        setattr(booking, field, value)
    booking.save(update_fields=[*updates, 'booked_at'])
    return booking


def _clean_submission(data):
    errors = []

    quick = data.get('quickMessage', False)
    if not isinstance(quick, bool):
        raise ConsultationError('quickMessage must be true or false.')

    fields = {'kind': ConsultationKind.QUICK if quick else ConsultationKind.FULL}
    for key in ('name', 'message', *OPTIONAL_TEXT_FIELDS, *CHOICE_FIELDS):
        try:
            fields[key] = _text(data, key)
        except ConsultationError as error:
            errors.append(str(error))
    if errors:
        raise ConsultationError(' '.join(errors))

    # Same rules and copy as ReachForm.tsx validate().
    if not fields['name']:
        errors.append('Please tell us your name.')
    if not fields['message']:
        errors.append(
            'Please add a short message.' if quick
            else 'Let us know what you’re trying to solve.'
        )
    if not quick and not fields['email']:
        errors.append('We need an email to reply.')
    elif fields['email']:
        try:
            _validate_email(fields['email'])
        except ValidationError:
            errors.append('That doesn’t look like a valid email.')
    if quick and not fields['phone']:
        errors.append('Add a phone number so we can reach you.')

    for key, choices in CHOICE_FIELDS.items():
        if fields[key] and fields[key] not in choices.values:
            errors.append(f"'{fields[key]}' is not a valid {key}.")

    for key in ('name', 'message', *OPTIONAL_TEXT_FIELDS):
        max_length = ConsultationRequest._meta.get_field(key).max_length
        if len(fields[key]) > max_length:
            errors.append(f'{key.capitalize()} must be at most {max_length} characters.')

    if errors:
        raise ConsultationError(' '.join(errors))
    return fields


def _text(data, key):
    """A trimmed string, with a missing or null value read as ''."""
    value = data.get(key)
    if value is None:
        return ''
    if not isinstance(value, str):
        raise ConsultationError(f'{key} must be a string.')
    return value.strip()


def _clean_ip(ip):
    ip = (ip or '').strip()
    try:
        validate_ipv46_address(ip)
    except ValidationError:
        return None
    return ip
