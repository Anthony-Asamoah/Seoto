from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class registerForm(UserCreationForm):
	first_name = forms.CharField(max_length=30, required=False, help_text='')
	last_name = forms.CharField(max_length=30, required=False, help_text='')
	email = forms.EmailField(max_length=254, help_text='Required. Enter a valid email address.')

	class Meta:
		model = User
		fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2',)

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		for field in self.fields.values():
			field.widget.attrs['class'] = 'form-control'
