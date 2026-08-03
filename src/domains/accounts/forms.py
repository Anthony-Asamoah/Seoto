from django import forms
from django.contrib.auth.forms import (
    UserCreationForm,
    AuthenticationForm,
    PasswordChangeForm,
    PasswordResetForm,
    SetPasswordForm
)
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from infrastructure.external_services.email_validation import is_valid_email
from infrastructure.core.mixins.views import HoneypotMixin, RecaptchaMixin


class LoginForm(RecaptchaMixin, HoneypotMixin, AuthenticationForm):
    recaptcha_action = 'login'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

        self.fields['password'].widget.attrs.update({
            'class': 'form-control password-input',
            'id': 'id_password'
        })
        self.fields['username'].widget.attrs.update({
            'id': 'id_username'
        })


class RegisterForm(RecaptchaMixin, HoneypotMixin, UserCreationForm):
    recaptcha_action = 'register'
    first_name = forms.CharField(max_length=30, required=False, help_text='')
    last_name = forms.CharField(max_length=30, required=False, help_text='')
    email = forms.EmailField(max_length=254, help_text='Required. Enter a valid email address.')

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'username', 'password1', 'password2',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

        # Add specific attributes for password fields to enable toggle functionality
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control password-input',
            'id': 'password1'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control password-input',
            'id': 'password2'
        })

    def clean_username(self):
        """Validate username is unique (case-insensitive)"""
        username = self.cleaned_data.get('username')

        # Check if username exists with case-insensitive search
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError(
                'A user with that username already exists (note: usernames are case-insensitive).'
            )

        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('A user with that email already exists.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        # Only call external API if reCAPTCHA + honeypot passed (no errors yet)
        email = cleaned_data.get('email')
        if email and not self.errors:
            if not is_valid_email(email):
                self.add_error('email', 'Please enter a valid email address.')
        return cleaned_data


class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

        # Add specific attributes for password fields to enable toggle functionality
        self.fields['old_password'].widget.attrs.update({
            'class': 'form-control password-input',
            'id': 'id_old_password'
        })
        self.fields['new_password1'].widget.attrs.update({
            'class': 'form-control password-input',
            'id': 'id_new_password1'
        })
        self.fields['new_password2'].widget.attrs.update({
            'class': 'form-control password-input',
            'id': 'id_new_password2'
        })


class CustomPasswordResetForm(RecaptchaMixin, HoneypotMixin, PasswordResetForm):
    recaptcha_action = 'password_reset'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

        self.fields['email'].widget.attrs.update({
            'id': 'id_email',
            'placeholder': 'Enter your email address'
        })


class CustomSetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

        # Add specific attributes for password fields to enable toggle functionality
        self.fields['new_password1'].widget.attrs.update({
            'class': 'form-control password-input',
            'id': 'id_new_password1'
        })
        self.fields['new_password2'].widget.attrs.update({
            'class': 'form-control password-input',
            'id': 'id_new_password2'
        })
