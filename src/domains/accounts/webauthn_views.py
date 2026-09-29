"""Passkey enrolment views, refused unless the session already proved any factor the account has.

The stock views only ask for a logged-in user, and a plain site login (`/accounts/login/`)
gives a session with no second factor. Registering a passkey also upgrades the session to
verified, so without this guard a stolen password could mint its own way into the admin.
"""

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django_otp_webauthn.views import (
    BeginCredentialAuthenticationView,
    BeginCredentialRegistrationView,
    CompleteCredentialAuthenticationView,
    CompleteCredentialRegistrationView,
)
from rest_framework.authentication import SessionAuthentication

from .services import requires_second_factor


class SessionAuth:
    """REST_FRAMEWORK turns authentication off project-wide; these views need the session user (and its CSRF check)."""

    authentication_classes = [SessionAuthentication]

    def perform_authentication(self, request):
        super().perform_authentication(request)
        # UNAUTHENTICATED_USER is None here, but the ceremony views read `request.user.is_authenticated`.
        if request.user is None:
            request.user = AnonymousUser()


class SecondFactorGuard(SessionAuth):
    def check_can_register(self):
        user = self.request.user
        if requires_second_factor(user) and not user.is_verified():
            raise PermissionDenied('Verify with your second factor before adding a passkey.')


class GuardedBeginRegistrationView(SecondFactorGuard, BeginCredentialRegistrationView):
    pass


class GuardedCompleteRegistrationView(SecondFactorGuard, CompleteCredentialRegistrationView):
    pass


class SessionBeginAuthenticationView(SessionAuth, BeginCredentialAuthenticationView):
    pass


class SessionCompleteAuthenticationView(SessionAuth, CompleteCredentialAuthenticationView):
    pass
