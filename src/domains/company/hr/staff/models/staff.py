from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from .choices import ContactChannel, CurrencyChoices, GenderChoices


class Position(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    reference_salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, choices=CurrencyChoices.choices, default=CurrencyChoices.GHS)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class MemberQuerySet(models.QuerySet):
    def active(self):
        return self.filter(ended_on__isnull=True)

    def former(self):
        return self.filter(ended_on__isnull=False)


class Member(models.Model):
    """basically our staff"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='member'
    )
    staff_id = models.CharField(max_length=50, unique=True)
    started_on = models.DateField()
    ended_on = models.DateField(null=True, blank=True)

    gender = models.CharField(max_length=10, choices=GenderChoices.choices, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    nationality = models.CharField(max_length=100, blank=True)
    hometown = models.CharField(max_length=100, blank=True)
    national_id = models.CharField(max_length=100, blank=True)

    profile_image = models.ImageField(upload_to='staff/profile_picture', blank=True)
    about = models.TextField(blank=True)
    is_public = models.BooleanField(default=False)

    objects = MemberQuerySet.as_manager()

    class Meta:
        ordering = ['user__first_name', 'user__last_name']

    def __str__(self):
        return self.user.get_full_name() or self.user.get_username()

    def clean(self):
        if self.ended_on and self.ended_on < self.started_on:
            raise ValidationError({'ended_on': 'End date cannot precede the start date.'})
        return super().clean()

    @property
    def is_active(self):
        return self.ended_on is None

    @property
    def age(self):
        if not self.date_of_birth: return None
        today = timezone.localdate()
        return today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )

    @property
    def primary_address(self):
        return self.addresses.filter(is_primary=True, is_active=True).first()

    def primary_contact(self, channel=ContactChannel.MOBILE):
        return self.contacts.filter(channel=channel, is_primary=True, is_active=True).first()

    @property
    def current_assignment(self):
        return self.assignments.filter(effective_from__lte=timezone.localdate()).first()

    @property
    def position(self):
        assignment = self.current_assignment
        return assignment.position if assignment else None


class Assignment(models.Model):
    """one row per position or pay change; the next row supersedes the previous"""
    member = models.ForeignKey('Member', on_delete=models.CASCADE, related_name='assignments')
    position = models.ForeignKey('Position', on_delete=models.PROTECT, related_name='assignments')
    salary = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, choices=CurrencyChoices.choices, default=CurrencyChoices.GHS)
    effective_from = models.DateField()
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-effective_from', '-id']
        constraints = [
            models.UniqueConstraint(fields=['member', 'effective_from'], name='unique_member_assignment_date'),
        ]

    def __str__(self):
        return f'{self.member} - {self.position} from {self.effective_from}'
