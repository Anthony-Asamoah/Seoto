from django.urls import path

from .apis import (
    ConsultationBookingAliasApi,
    ConsultationBookingApi,
    ConsultationCreateAliasApi,
    ConsultationCreateApi,
)

# The frontend posts without a trailing slash, and APPEND_SLASH cannot redirect a POST.
urlpatterns = [
    path('consultations', ConsultationCreateApi.as_view(), name='consultations_create'),
    path('consultations/', ConsultationCreateAliasApi.as_view()),
    path(
        'consultations/<uuid:reference_id>/booking',
        ConsultationBookingApi.as_view(), name='consultations_booking_create',
    ),
    path('consultations/<uuid:reference_id>/booking/', ConsultationBookingAliasApi.as_view()),
]
