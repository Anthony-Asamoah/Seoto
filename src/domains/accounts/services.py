"""Issuing and confirming a user's second factor.

Shared by three callers that all need the same device lifecycle: the `setup_admin_totp`
management command, the admin's User change page, and the emailed enrolment page.
"""

from base64 import b32encode

import qrcode
import qrcode.image.svg
from django.core import signing
from django.utils.safestring import mark_safe
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp_webauthn.models import WebAuthnCredential

DEVICE_NAME = 'Authenticator'
BACKUP_DEVICE_NAME = 'Backup codes'
BACKUP_CODE_COUNT = 10

SETUP_LINK_SALT = 'accounts.totp-setup'
SETUP_LINK_MAX_AGE = 60 * 60 * 24


def issue_totp_device(user, name=DEVICE_NAME, confirmed=False):
    """Replace every authenticator the user has with one fresh, unconfirmed secret."""
    TOTPDevice.objects.filter(user=user).delete()
    return TOTPDevice.objects.create(user=user, name=name, confirmed=confirmed)


def pending_device(user):
    return TOTPDevice.objects.filter(user=user, confirmed=False).first()


def has_confirmed_device(user):
    return TOTPDevice.objects.filter(user=user, confirmed=True).exists()


def has_passkey(user):
    return WebAuthnCredential.objects.filter(user=user, confirmed=True).exists()


def requires_second_factor(user):
    """Backup codes are excluded: they exist from the moment setup starts, before it is confirmed."""
    return user.is_authenticated and (has_confirmed_device(user) or has_passkey(user))


def issue_backup_codes(user, count=BACKUP_CODE_COUNT):
    device, _ = StaticDevice.objects.get_or_create(user=user, name=BACKUP_DEVICE_NAME)
    device.confirmed = True
    device.save(update_fields=['confirmed'])
    device.token_set.all().delete()
    return [
        StaticToken.objects.create(device=device, token=StaticToken.random_token()).token
        for _ in range(count)
    ]


def backup_codes(user):
    return list(
        StaticToken.objects
        .filter(device__user=user, device__name=BACKUP_DEVICE_NAME)
        .values_list('token', flat=True)
    )


def secret_b32(device):
    """The shared secret in the form authenticator apps accept for manual entry."""
    return b32encode(device.bin_key).decode()


def qr_svg(config_url):
    """Inline SVG so the QR needs no image file, no data URI and no PIL."""
    image = qrcode.make(config_url, image_factory=qrcode.image.svg.SvgPathImage, border=1)
    return mark_safe(image.to_string(encoding='unicode'))


def make_setup_token(device):
    return signing.TimestampSigner(salt=SETUP_LINK_SALT).sign(f'{device.pk}:{device.user_id}')


def read_setup_token(token):
    """The device a setup link points at, or None once the link is spent, stale or forged."""
    try:
        value = signing.TimestampSigner(salt=SETUP_LINK_SALT).unsign(
            token, max_age=SETUP_LINK_MAX_AGE
        )
        device_pk, user_pk = value.split(':')
    except (signing.BadSignature, ValueError):
        return None

    # Confirmed devices end the link's life: that is what makes it single-use.
    return TOTPDevice.objects.filter(pk=device_pk, user_id=user_pk, confirmed=False).first()


def begin_totp_setup(user, confirm=False, rotate=False):
    """The pending device to show, or None when that would wipe a working one unconfirmed."""
    if has_confirmed_device(user) and not confirm:
        return None
    device = pending_device(user)
    if device is None or confirm or rotate:
        device = issue_totp_device(user)
        issue_backup_codes(user)
    return device


def confirm_device(device, code):
    if not device.verify_token(code):
        return False
    device.confirmed = True
    device.save(update_fields=['confirmed'])
    return True


def security_context(user):
    if has_confirmed_device(user):
        totp_status = 'active'
    else:
        totp_status = 'pending' if pending_device(user) else 'none'
    return {
        'totp_status': totp_status,
        'passkeys': WebAuthnCredential.objects.filter(user=user, confirmed=True).order_by('-created_at'),
        'backup_code_count': len(backup_codes(user)),
    }
