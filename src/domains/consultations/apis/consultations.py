from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import status as http_status
from rest_framework.exceptions import ParseError
from rest_framework.parsers import JSONParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from domains.home.utils import get_client_ip

from ..models import ConsultationBooking
from ..serializers import (
    BookingConfirmationSerializer,
    ConsultationCreatedSerializer,
    ConsultationSubmissionSerializer,
    ErrorSerializer,
    OkSerializer,
)
from ..services import (
    ConsultationError,
    create_consultation,
    decoy_consultation,
    honeypot_tripped,
    record_booking,
)


class ConsultationCreateApi(APIView):
    """POST /v1/consultations — the reach-out form, quick message or full."""

    permission_classes = (AllowAny,)
    parser_classes = (JSONParser,)

    @extend_schema(
        operation_id='consultations_create',
        summary='Submit a consultation request or quick message',
        request=ConsultationSubmissionSerializer,
        responses={200: ConsultationCreatedSerializer, 400: ErrorSerializer},
    )
    def post(self, request):
        try:
            data = _json_object(request)
            if honeypot_tripped(data):
                return _created(decoy_consultation(data), settings.CALENDLY_URL)

            consultation = create_consultation(
                data,
                ip=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
            )
        except ConsultationError as error:
            return _bad_request(error)

        return _created(consultation, consultation.booking.scheduling_url)


class ConsultationBookingApi(APIView):
    """POST /v1/consultations/<reference_id>/booking — Calendly confirmed a slot."""

    permission_classes = (AllowAny,)
    parser_classes = (JSONParser,)

    @extend_schema(
        operation_id='consultations_booking_create',
        summary='Record the Calendly event booked for a consultation',
        request=BookingConfirmationSerializer,
        responses={200: OkSerializer, 400: ErrorSerializer, 404: ErrorSerializer},
    )
    def post(self, request, reference_id):
        try:
            record_booking(reference_id, _json_object(request).get('event'))
        except ConsultationBooking.DoesNotExist:
            return Response(
                {'message': 'Consultation not found.'}, status=http_status.HTTP_404_NOT_FOUND
            )
        except ConsultationError as error:
            return _bad_request(error)

        return Response({'ok': True})


# Trailing-slash aliases, kept out of the schema so the operation ids stay unique.
@extend_schema(exclude=True)
class ConsultationCreateAliasApi(ConsultationCreateApi):
    pass


@extend_schema(exclude=True)
class ConsultationBookingAliasApi(ConsultationBookingApi):
    pass


def _json_object(request):
    try:
        data = request.data
    except ParseError:
        raise ConsultationError('Request body must be valid JSON.')
    if not isinstance(data, dict):
        raise ConsultationError('Request body must be a JSON object.')
    return data


def _created(consultation, scheduling_url):
    return Response(ConsultationCreatedSerializer({
        'ok': True,
        'referenceId': consultation.reference_id,
        'booking': {
            'provider': 'calendly',
            'schedulingUrl': scheduling_url,
            'prefill': {'name': consultation.name, 'email': consultation.email or None},
        },
    }).data)


def _bad_request(error):
    return Response({'message': str(error)}, status=http_status.HTTP_400_BAD_REQUEST)
