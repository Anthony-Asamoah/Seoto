from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


class LoginForm(AuthenticationForm):
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


class RegisterForm(UserCreationForm):
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
