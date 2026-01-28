import logging

from django import forms
from django.core.exceptions import ValidationError

from seoto.external_services.recaptcha import is_human



class HoneypotMixin:
    """Mixin to add honeypot spam protection to forms."""
    honeypot_field_name = 'website'  # Looks legitimate to bots

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[self.honeypot_field_name] = forms.CharField(
            required=False,
            widget=forms.TextInput(attrs={
                'class': 'hp-field',
                'tabindex': '-1',
                'autocomplete': 'off',
            })
        )

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get(self.honeypot_field_name):
            raise ValidationError('Bot detected.')
        return cleaned_data


class RecaptchaMixin:
    """Mixin to add reCAPTCHA v3 protection to forms."""
    recaptcha_action = 'form_submit'  # Override in subclass

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()

        if self.request:
            token = self.request.POST.get('g-recaptcha-response', '')
            human, score = is_human(token, action=self.recaptcha_action)

            logging.info(f"reCAPTCHA score for {self.recaptcha_action}: {score}")

            if not human:
                logging.warning(f"reCAPTCHA failed for {self.recaptcha_action}: score={score}")
                raise ValidationError('Security verification failed. Please try again.')

        return cleaned_data
