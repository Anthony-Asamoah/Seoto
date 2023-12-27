from datetime import datetime

from django.conf import settings
from django.core.mail import send_mail
from django.db import models
from django.utils import timezone

from seoto.utils import Validators


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
