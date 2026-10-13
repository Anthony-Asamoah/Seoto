from rest_framework import serializers

from .models import Budget, Interest, Timeline


# Field names are camelCase to match seoto_ui's api/client.ts contract.
class ConsultationSubmissionSerializer(serializers.Serializer):
    """Request body, for the schema only: the rules live in ``services``."""

    quickMessage = serializers.BooleanField()
    name = serializers.CharField()
    email = serializers.EmailField(required=False, allow_null=True, allow_blank=True)
    company = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    phone = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    interest = serializers.ChoiceField(Interest.choices, required=False, allow_null=True, allow_blank=True)
    message = serializers.CharField()
    budget = serializers.ChoiceField(Budget.choices, required=False, allow_null=True, allow_blank=True)
    timeline = serializers.ChoiceField(Timeline.choices, required=False, allow_null=True, allow_blank=True)
    honeypot = serializers.CharField(required=False, allow_blank=True)
    recaptchaToken = serializers.CharField(
        required=False, allow_null=True, help_text='Accepted but not verified yet.',
    )


class BookingPrefillSerializer(serializers.Serializer):
    name = serializers.CharField()
    email = serializers.EmailField(allow_null=True)


class BookingDetailsSerializer(serializers.Serializer):
    provider = serializers.CharField()
    schedulingUrl = serializers.URLField()
    prefill = BookingPrefillSerializer()


class ConsultationCreatedSerializer(serializers.Serializer):
    ok = serializers.BooleanField()
    referenceId = serializers.UUIDField()
    booking = BookingDetailsSerializer()


class BookingEventSerializer(serializers.Serializer):
    uri = serializers.URLField(required=False)
    inviteeUri = serializers.URLField(required=False)
    startTime = serializers.DateTimeField(required=False)


class BookingConfirmationSerializer(serializers.Serializer):
    event = BookingEventSerializer()


class OkSerializer(serializers.Serializer):
    ok = serializers.BooleanField()


class ErrorSerializer(serializers.Serializer):
    message = serializers.CharField()
