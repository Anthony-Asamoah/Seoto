from django.core.exceptions import ValidationError
from django.db import models

from .choices import MembershipRole


class Team(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    members = models.ManyToManyField('Member', related_name='teams', through='Membership')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def lead(self):
        membership = self.memberships.filter(role=MembershipRole.LEAD, left_on__isnull=True).first()
        return membership.member if membership else None


class MembershipQuerySet(models.QuerySet):
    def active(self):
        return self.filter(left_on__isnull=True)


class Membership(models.Model):
    team = models.ForeignKey('Team', on_delete=models.CASCADE, related_name='memberships')
    member = models.ForeignKey('Member', on_delete=models.PROTECT, related_name='memberships')
    role = models.CharField(max_length=20, choices=MembershipRole.choices, default=MembershipRole.MEMBER)
    joined_on = models.DateField()
    left_on = models.DateField(null=True, blank=True)

    objects = MembershipQuerySet.as_manager()

    class Meta:
        ordering = ['-joined_on']
        constraints = [
            models.UniqueConstraint(
                fields=['team', 'member'], condition=models.Q(left_on__isnull=True),
                name='unique_active_team_membership',
            ),
        ]

    def __str__(self):
        return f'{self.member} in {self.team}'

    def clean(self):
        if self.left_on and self.left_on < self.joined_on:
            raise ValidationError({'left_on': 'Leave date cannot precede the join date.'})
        return super().clean()

    @property
    def is_active(self):
        return self.left_on is None
