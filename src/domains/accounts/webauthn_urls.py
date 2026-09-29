from django.urls import path
from django.views.i18n import JavaScriptCatalog

from .webauthn_views import (
    GuardedBeginRegistrationView,
    GuardedCompleteRegistrationView,
    SessionBeginAuthenticationView,
    SessionCompleteAuthenticationView,
)

app_name = 'otp_webauthn'

urlpatterns = [
    path('registration/begin/', GuardedBeginRegistrationView.as_view(), name='credential-registration-begin'),
    path('registration/complete/', GuardedCompleteRegistrationView.as_view(), name='credential-registration-complete'),
    path('authentication/begin/', SessionBeginAuthenticationView.as_view(), name='credential-authentication-begin'),
    path('authentication/complete/', SessionCompleteAuthenticationView.as_view(), name='credential-authentication-complete'),
    path('jsi18n/', JavaScriptCatalog.as_view(packages=['django_otp_webauthn']), name='js-i18n-catalog'),
]
