from datetime import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import models
from django.utils import timezone

from seoto.model_validators import Validators
from utils.enums import DefaultEnum


class IntroLinks(models.Model):
    label = models.CharField(max_length=250)
    url = models.URLField(max_length=1000)


class Intro(models.Model):
    first_name = models.CharField(max_length=250)
    last_name = models.CharField(max_length=250)
    email = models.EmailField(max_length=250)
    phone = models.CharField(max_length=17)
    country = models.CharField(max_length=250, null=True, blank=True)
    city = models.CharField(max_length=250, null=True, blank=True)
    nationality = models.CharField(max_length=250, null=True, blank=True)
    date_of_birth = models.CharField(max_length=250, null=True, blank=True)
    profile_image = models.ImageField(upload_to='author/profile_picture')
    about = models.TextField(blank=True, null=True)
    links = models.ManyToManyField("IntroLinks")


class CertificateType(DefaultEnum):
    HIGH_SCHOOL_DIPLOMA = "High School Diploma"
    ASSOCIATE_DEGREE = "Associate Degree"
    BACHELORS_DEGREE = "Bachelor's Degree"
    MASTERS_DEGREE = "Master's Degree"
    DOCTORATE_DEGREE = "Doctorate Degree"
    PROFESSIONAL_DEGREE = "Professional Degree"
    CERTIFICATE = "Certificate"
    DIPLOMA = "Diploma"
    POSTGRADUATE_CERTIFICATE = "Postgraduate Certificate"
    POSTGRADUATE_DIPLOMA = "Postgraduate Diploma"
    TRADE_CERTIFICATE = "Trade Certificate"
    VOCATIONAL_CERTIFICATE = "Vocational Certificate"
    HONORARY_DOCTORATE = "Honorary Doctorate"
    OTHER = "Other"


class Education(models.Model):
    School = models.CharField(max_length=250)
    certificate_title = models.CharField(max_length=250)
    certificate_type = models.CharField(max_length=250, choices=CertificateType.key_value_pairs())
    other_certificate_type = models.CharField(
        max_length=250, blank=True, null=True,
    )
    start_date = models.DateField()
    end_date = models.DateField()
    city = models.CharField(max_length=250, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    def clean(self):
        self.validate_certificate_type()
        return super().clean()

    def save(self, *args, **kwargs):
        self.validate_certificate_type()
        return super().save(*args, **kwargs)

    def validate_certificate_type(self):
        if self.certificate_type == CertificateType.OTHER.name and not self.other_certificate_type:
            raise ValidationError(dict(other_certificate_type='Kindly specify the type of certificate.'))


class JobExperience(models.Model):
    job_title = models.CharField(max_length=250)
    employer = models.CharField(max_length=250)
    start_date = models.DateField()
    end_date = models.DateField()
    city = models.CharField(max_length=250, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.job_title


class Stack(models.Model):
    is_active = models.BooleanField(default=False)
    label = models.CharField(max_length=100, default=f'Developer Stack')
    languages = models.TextField(blank=True, null=True)
    frameworks = models.TextField(blank=True, null=True)
    databases = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name_plural = 'Stack'

    def __str__(self):
        if self.label: return self.label
        return f'Developer Stack {self.id}'


class Message(models.Model):
    name = models.CharField(null=False, blank=False, max_length=200, validators=[Validators.str])
    email = models.EmailField(null=False, blank=False, validators=[Validators.str])
    subject = models.CharField(max_length=200, blank=False, null=False, validators=[Validators.str])
    message = models.TextField(null=False, blank=False, validators=[Validators.str])
    submitted_on = models.DateTimeField(default=timezone.now)
    replied = models.BooleanField(default=False)

    @property
    def pretty_time(self):
        t = datetime.now().strftime("%a, %d %b %Y %I:%M %p.")
        if t[0] == "0": t = t[1:]
        return t

    def __str__(self):
        return f'Message from {self.name}'

    def forward_to_email(self):
        mail_title = f'Seoto - {self.subject}'
        mail_body = f'''{self.message}\n\nSent on {self.pretty_time}\nFrom {self.name}\n{self.email}'''
        mail_sender = settings.EMAIL_HOST_USER
        mail_recipient = [settings.EMAIL_HOST_USER]
        send_mail(mail_title, mail_body, mail_sender, mail_recipient, fail_silently=False)
