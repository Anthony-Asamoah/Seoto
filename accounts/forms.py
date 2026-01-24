from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm, PasswordResetForm, SetPasswordForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


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


class LoginForm(HoneypotMixin, AuthenticationForm):
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


class RegisterForm(HoneypotMixin, UserCreationForm):
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


class CustomPasswordResetForm(PasswordResetForm):
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
