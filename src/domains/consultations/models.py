import uuid

from django.db import models

from infrastructure.utils.choices import BaseChoices


class ConsultationKind(BaseChoices):
    QUICK = 'quick', 'Quick message'
    FULL = 'full', 'Full consultation'


# Values mirror the option lists in seoto_ui's reach-out/data.ts.
class Interest(BaseChoices):
    LAUNCH_FAST = 'launch-fast', 'A website / launch fast'
    PROVEN_SOFTWARE = 'proven-software', 'Proven software / a product'
    CUSTOM_BUILD = 'custom-build', 'A custom build'
    NOT_SURE = 'not-sure', 'Not sure yet'


class Budget(BaseChoices):
    UNDECIDED = 'undecided', 'Not sure yet'
    UNDER_1K = 'under-1k', 'Under $1,000'
    FROM_1K_TO_5K = '1k-5k', '$1,000 – $5,000'
    FROM_5K_TO_15K = '5k-15k', '$5,000 – $15,000'
    OVER_15K = '15k-plus', '$15,000+'


class Timeline(BaseChoices):
    ASAP = 'asap', 'As soon as possible'
    ONE_TO_THREE_MONTHS = '1-3-months', 'In 1 – 3 months'
    THREE_TO_SIX_MONTHS = '3-6-months', 'In 3 – 6 months'
    EXPLORING = 'exploring', 'Just exploring'


class ConsultationRequest(models.Model):
    """One submission of the marketing site's reach-out form."""

    reference_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    kind = models.CharField(max_length=8, choices=ConsultationKind.choices)

    name = models.CharField(max_length=120)
    email = models.EmailField(max_length=254, blank=True)
    company = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    interest = models.CharField(max_length=32, choices=Interest.choices, blank=True)
    message = models.TextField(max_length=5000)
    budget = models.CharField(max_length=32, choices=Budget.choices, blank=True)
    timeline = models.CharField(max_length=32, choices=Timeline.choices, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    source_ip = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} ({self.get_kind_display()})'


class ConsultationBooking(models.Model):
    """The Calendly side of a request; event fields fill in once a slot is booked."""

    consultation = models.OneToOneField(
        ConsultationRequest, on_delete=models.CASCADE, related_name='booking',
    )
    provider = models.CharField(max_length=20, default='calendly')
    scheduling_url = models.URLField(max_length=500)
    event_uri = models.URLField(max_length=500, blank=True)
    invitee_uri = models.URLField(max_length=500, blank=True)
    start_time = models.DateTimeField(blank=True, null=True)
    booked_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Booking for {self.consultation}'

    @property
    def is_booked(self):
        return bool(self.event_uri or self.start_time)
