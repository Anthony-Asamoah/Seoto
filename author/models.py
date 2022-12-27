from django.db import models
from django.forms import ModelForm, TextInput
from django.utils import timezone


class stack(models.Model):
	is_active = models.BooleanField(default=False)
	label = models.CharField(max_length=100, default=f'Developer stack')
	languages = models.TextField(blank=True, null=True)
	frameworks = models.TextField(blank=True, null=True)
	databases = models.TextField(blank=True, null=True)

	class Meta:
		verbose_name_plural = 'stack'

	def __str__(self):
		if self.label:
			return self.label
		return f'Developer stack {self.id}'


class message(models.Model):
	name = models.CharField(null=False, blank=False, max_length=200)
	email = models.EmailField(null=False, blank=False)
	subject = models.CharField(max_length=200, blank=False, null=False)
	message = models.TextField(null=False, blank=False)
	submitted_on = models.DateTimeField(default=timezone.now)
	replied = models.BooleanField(default=False)

	def __str__(self):
		return f'Message from {self.name}'


class contact_form(ModelForm):
	class Meta:
		model = message
		fields = ['name', 'email', 'subject', 'message']
		widgets = {
			'name': TextInput(attrs={'placeholder': 'First name & Last name'}),
		}

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		for field in self.fields.values():
			field.widget.attrs['class'] = 'form-control'
