from django.db import models
from django.contrib.auth.models import User


class user_profile(models.Model):
	user = models.OneToOneField(User, on_delete=models.CASCADE)
	contact = models.CharField(max_length=15, null=True, blank=True)
	picture = models.ImageField(upload_to=f'accounts/%Y-%m-%d', blank=True, null=True)

	def __str__(self):
		return f'{self.user.username}'
