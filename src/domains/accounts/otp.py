"""Shared second-factor behaviour for the admin and the public login forms."""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.http import HttpResponseNotAllowed, JsonResponse
from django.views.decorators.cache import never_cache
from django_otp.forms import OTPAuthenticationFormMixin

from .services import has_confirmed_device, has_passkey, requires_second_factor


class OptionalOTPMixin(OTPAuthenticationFormMixin):
    """The code is only demanded from accounts that have enrolled a device."""

    otp_failed = False

    def clean_otp(self, user):
        if user is not None and not requires_second_factor(user):
            return
        try:
            if user is not None and has_passkey(user) and not has_confirmed_device(user):
                raise ValidationError('This account signs in with a passkey.', code='passkey_only')
            super().clean_otp(user)
        except ValidationError:
            self.otp_failed = True
            raise


@never_cache
def login_factors_response(request, staff_only=False):
    """Tell a login page whether to ask for a code. Unknown names look like unenrolled ones."""
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    User = get_user_model()
    username = request.POST.get('username', '').strip()
    lookup = {User.USERNAME_FIELD: username, 'is_active': True}
    if staff_only:
        lookup['is_staff'] = True
    user = User._default_manager.filter(**lookup).first() if username else None

    needs_code = bool(user and has_confirmed_device(user))
    passkey_only = bool(user and not needs_code and has_passkey(user))
    return JsonResponse({'code': needs_code, 'passkey_only': passkey_only})
