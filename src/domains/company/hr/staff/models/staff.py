from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction
from django.db.models import Q
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


class StaffIdSequence(models.Model):
    """single-row high-water mark, so a deleted member never frees their number"""
    last_issued = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'Staff ID sequence'
        verbose_name_plural = 'Staff ID sequence'

    def __str__(self):
        return f'last issued: {self.last_issued}'

    @classmethod
    def claim(cls):
        with transaction.atomic():
            row = cls.objects.select_for_update().first() or cls.objects.create()
            row.last_issued = models.F('last_issued') + 1
            row.save(update_fields=['last_issued'])
            row.refresh_from_db(fields=['last_issued'])
        return row.last_issued


class MemberQuerySet(models.QuerySet):
    def active(self):
        return self.filter(ended_on__isnull=True)

    def former(self):
        return self.filter(ended_on__isnull=False)


class Member(models.Model):
    """basically our staff"""
    STAFF_ID_PREFIX = 'SEO'
    STAFF_ID_PADDING = 4
    STAFF_ID_ATTEMPTS = 5

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='member'
    )
    staff_id = models.CharField('Staff ID', max_length=50, unique=True, editable=False)
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

    def save(self, *args, **kwargs):
        if self.staff_id:
            return super().save(*args, **kwargs)

        # The unique index is the real guarantee; retry the sequence it rejects.
        for attempt in range(self.STAFF_ID_ATTEMPTS):
            self.staff_id = self.next_staff_id()
            try:
                with transaction.atomic():
                    return super().save(*args, **kwargs)
            except IntegrityError:
                if attempt == self.STAFF_ID_ATTEMPTS - 1:
                    raise
                self.staff_id = ''

    @classmethod
    def next_staff_id(cls):
        return f'{cls.STAFF_ID_PREFIX}-{StaffIdSequence.claim():0{cls.STAFF_ID_PADDING}d}'

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
    def current_assignments(self):
        return self.assignments.current().select_related('position')

    @property
    def current_assignment(self):
        return self.current_assignments.first()

    @property
    def positions(self):
        return [assignment.position for assignment in self.current_assignments]

    @property
    def position(self):
        assignment = self.current_assignment
        return assignment.position if assignment else None


class AssignmentQuerySet(models.QuerySet):
    def current(self, on=None):
        on = on or timezone.localdate()
        return self.filter(effective_from__lte=on).filter(
            Q(effective_to__isnull=True) | Q(effective_to__gte=on)
        )


class Assignment(models.Model):
    """one row per position a member holds; several may run concurrently"""
    member = models.ForeignKey('Member', on_delete=models.CASCADE, related_name='assignments')
    position = models.ForeignKey('Position', on_delete=models.PROTECT, related_name='assignments')
    salary = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, choices=CurrencyChoices.choices, default=CurrencyChoices.GHS)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True, help_text='Leave blank while the member still holds it.')
    note = models.CharField(max_length=255, blank=True)

    objects = AssignmentQuerySet.as_manager()

    class Meta:
        ordering = ['-effective_from', '-id']
        constraints = [
            models.UniqueConstraint(
                fields=['member', 'position', 'effective_from'], name='unique_member_position_start'
            ),
            models.CheckConstraint(
                condition=Q(effective_to__isnull=True) | Q(effective_to__gte=models.F('effective_from')),
                name='assignment_ends_after_it_starts',
            ),
        ]

    def __str__(self):
        return f'{self.member} - {self.position} from {self.effective_from}'

    @property
    def is_current(self):
        today = timezone.localdate()
        return self.effective_from <= today and (self.effective_to is None or self.effective_to >= today)

    def overlaps(self, other):
        """same position, intersecting date ranges (an open end runs forever)"""
        if self.position_id != other.position_id:
            return False
        if not self.effective_from or not other.effective_from:
            return False
        starts_before_other_ends = other.effective_to is None or self.effective_from <= other.effective_to
        ends_after_other_starts = self.effective_to is None or self.effective_to >= other.effective_from
        return starts_before_other_ends and ends_after_other_starts

    OVERLAP_ERROR = (
        'This member already holds this position over an overlapping period. '
        'End the earlier assignment before starting a new one.'
    )

    def clean(self):
        if self.effective_from and self.effective_to and self.effective_to < self.effective_from:
            raise ValidationError({'effective_to': 'End date cannot precede the start date.'})
        # The member inline validates the whole formset instead; a row and its replacement are saved together.
        if not getattr(self, 'skip_overlap_check', False):
            self.validate_no_overlap()
        return super().clean()

    def validate_no_overlap(self):
        if not (self.member_id and self.position_id and self.effective_from):
            return
        siblings = Assignment.objects.filter(
            member_id=self.member_id, position_id=self.position_id
        ).exclude(pk=self.pk)
        if any(self.overlaps(sibling) for sibling in siblings):
            raise ValidationError(self.OVERLAP_ERROR)
