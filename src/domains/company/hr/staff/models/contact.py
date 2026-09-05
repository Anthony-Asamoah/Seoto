from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import models

from infrastructure.utils.validators import normalize_phone, validate_phone
from .choices import AddressType, ContactChannel, ContactUsage

PHONE_CHANNELS = frozenset({ContactChannel.MOBILE, ContactChannel.LANDLINE, ContactChannel.WHATSAPP})


class ContactQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def primary(self):
        return self.filter(is_primary=True, is_active=True)


class Contact(models.Model):
    """one reachable channel — a phone number, an inbox, a profile URL"""
    member = models.ForeignKey('Member', on_delete=models.CASCADE, related_name='contacts')
    channel = models.CharField(max_length=20, choices=ContactChannel.choices)
    value = models.CharField(max_length=255)
    usage = models.CharField(max_length=20, choices=ContactUsage.choices, default=ContactUsage.PERSONAL)
    label = models.CharField(max_length=100, blank=True)
    is_primary = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_public = models.BooleanField(default=False)
    verified_on = models.DateField(null=True, blank=True)
    note = models.CharField(max_length=255, blank=True)

    objects = ContactQuerySet.as_manager()

    class Meta:
        ordering = ['-is_primary', 'channel', 'value']
        constraints = [
            models.UniqueConstraint(
                fields=['member', 'channel', 'value'], name='unique_member_contact_value',
            ),
            models.UniqueConstraint(
                fields=['member', 'channel'], condition=models.Q(is_primary=True),
                name='unique_primary_contact_per_channel',
            ),
        ]

    def __str__(self):
        return f'{self.get_channel_display()}: {self.value}'

    def clean(self):
        if self.value:
            if self.channel == ContactChannel.EMAIL:
                try:
                    validate_email(self.value)
                except ValidationError:
                    raise ValidationError({'value': 'Enter a valid email address.'})
            elif self.channel in PHONE_CHANNELS:
                try:
                    validate_phone(self.value)
                except ValidationError as e:
                    raise ValidationError({'value': e.messages[0]})
                self.value = normalize_phone(self.value)
        return super().clean()

    def save(self, *args, **kwargs):
        if self.channel in PHONE_CHANNELS and self.value:
            self.value = normalize_phone(self.value)
        return super().save(*args, **kwargs)

    @property
    def is_verified(self):
        return self.verified_on is not None


class AddressQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)


class Address(models.Model):
    member = models.ForeignKey('Member', on_delete=models.CASCADE, related_name='addresses')
    address_type = models.CharField(max_length=20, choices=AddressType.choices, default=AddressType.RESIDENTIAL)
    house_number = models.CharField(max_length=100, blank=True)
    street = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    region = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    digital_address = models.CharField(max_length=15, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    is_primary = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    objects = AddressQuerySet.as_manager()

    class Meta:
        verbose_name_plural = 'Addresses'
        ordering = ['-is_primary', 'city', 'street']
        constraints = [
            models.UniqueConstraint(
                fields=['member'], condition=models.Q(is_primary=True),
                name='unique_primary_address_per_member',
            ),
        ]

    def __str__(self):
        return self.full_address or self.get_address_type_display()

    @property
    def full_address(self):
        parts = [self.house_number, self.street, self.city, self.region, self.postal_code, self.country]
        return ', '.join(part for part in parts if part)
