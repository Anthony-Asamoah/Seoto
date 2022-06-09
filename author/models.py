from django.forms import ModelForm, TextInput
from django.utils import timezone
from django.db import models


class contact(models.Model):
	name = models.CharField(null=False, blank=False, max_length=200)
	email = models.EmailField(null=False, blank=False)
	subject = models.CharField(max_length=200, blank=False, null=False)
	message = models.TextField(null=False, blank=False)
	submitted_on = models.DateTimeField(default=timezone.now())
	replied = models.BooleanField(default=False)

	def __str__(self):
		return f'Message from {self.name}'


class contact_form(ModelForm):
	class Meta:
		model = contact
		fields = '__all__'
		widgets = {
			'name': TextInput(attrs={'placeholder': 'First name & Last name'}),
		}

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		for field in self.fields.values():
			field.widget.attrs['class'] = 'form-control'
