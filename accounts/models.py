from functools import partial

from django.contrib.auth.models import User
from django.db import models

from accounts.utils import user_directory_file_path


class user_profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    contact = models.CharField(max_length=15, null=True, blank=True)
    picture = models.ImageField(
        upload_to=partial(user_directory_file_path, prefix='accounts/%Y-%m-%d'),
        blank=True, null=True
    )

    def __str__(self):
        return f'{self.user.username}'
