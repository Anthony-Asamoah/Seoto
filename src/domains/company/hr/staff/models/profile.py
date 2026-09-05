from django.core.exceptions import ValidationError
from django.db import models

from .choices import CertificateType


class ProfileSection(models.Model):
    """shared shape for the ordered, hideable records on a member's public profile"""
    order = models.PositiveSmallIntegerField(default=1, blank=True)
    hidden = models.BooleanField(default=False)

    class Meta:
        abstract = True
        ordering = ['order']

    def validate_date_range(self):
        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValidationError({'end_date': 'End date cannot precede the start date.'})


class Education(ProfileSection):
    member = models.ForeignKey('Member', on_delete=models.CASCADE, related_name='education')
    school = models.CharField(max_length=250)
    certificate_title = models.CharField(max_length=250)
    certificate_type = models.CharField(max_length=250, choices=CertificateType.choices)
    other_certificate_type = models.CharField(max_length=250, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    city = models.CharField(max_length=250, blank=True)
    description = models.TextField(blank=True)

    class Meta(ProfileSection.Meta):
        abstract = False
        verbose_name_plural = 'Education'

    def __str__(self):
        return f'{self.certificate_title} - {self.school}'

    def clean(self):
        self.validate_certificate_type()
        self.validate_date_range()
        return super().clean()

    def save(self, *args, **kwargs):
        self.validate_certificate_type()
        return super().save(*args, **kwargs)

    def validate_certificate_type(self):
        # `other_certificate_type` is what the template renders.
        if self.certificate_type == CertificateType.OTHER:
            if not self.other_certificate_type:
                raise ValidationError({'other_certificate_type': 'Kindly specify the type of certificate.'})
            return
        self.other_certificate_type = self.certificate_type


class Certificate(ProfileSection):
    """training and certification, whether we sponsored it or they brought it"""
    member = models.ForeignKey('Member', on_delete=models.CASCADE, related_name='certificates')
    course_name = models.CharField(max_length=255)
    issuing_body = models.CharField(max_length=255)
    reference = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    awarded_on = models.DateField(null=True, blank=True)
    expires_on = models.DateField(null=True, blank=True)
    is_sponsored = models.BooleanField(default=False)

    class Meta(ProfileSection.Meta):
        abstract = False
        ordering = ['-awarded_on', 'order']

    def __str__(self):
        return f'{self.course_name} - {self.issuing_body}'


class JobExperience(ProfileSection):
    """employment before Seoto; current work is an Assignment"""
    member = models.ForeignKey('Member', on_delete=models.CASCADE, related_name='job_experience')
    job_title = models.CharField(max_length=250)
    employer = models.CharField(max_length=250)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    city = models.CharField(max_length=250, blank=True)
    description = models.TextField(blank=True)

    class Meta(ProfileSection.Meta):
        abstract = False

    def __str__(self):
        return f'{self.job_title} at {self.employer}'

    def clean(self):
        self.validate_date_range()
        return super().clean()


class Hobby(ProfileSection):
    member = models.ForeignKey('Member', on_delete=models.CASCADE, related_name='hobbies')
    description = models.CharField(max_length=500)

    class Meta(ProfileSection.Meta):
        abstract = False
        verbose_name_plural = 'Hobbies'

    def __str__(self):
        return self.description


class Specialisation(ProfileSection):
    member = models.ForeignKey('Member', on_delete=models.CASCADE, related_name='specialisations')
    name = models.CharField(max_length=100)
    tools = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta(ProfileSection.Meta):
        abstract = False
        verbose_name_plural = 'Specialisations'
        constraints = [
            models.UniqueConstraint(fields=['member', 'name'], name='unique_member_specialisation'),
        ]

    def __str__(self):
        return self.name
