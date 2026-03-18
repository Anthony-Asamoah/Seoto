from functools import partial

from django.contrib.auth.models import User
from django.core.files.uploadedfile import UploadedFile
from django.db import models

from accounts.utils import user_directory_file_path


class user_profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    contact = models.CharField(max_length=15, null=True, blank=True)
    picture = models.ImageField(
        upload_to=partial(user_directory_file_path, prefix='accounts/%Y-%m-%d'),
        blank=True, null=True
    )
    picture_thumbnail = models.ImageField(upload_to='accounts/thumbs', blank=True, null=True)

    class Meta:
        verbose_name_plural = "User Profiles"

    def save(self, *args, **kwargs):
        new_picture = isinstance(self.picture, UploadedFile)
        first_save = not self.pk
        super().save(*args, **kwargs)
        if new_picture or (first_save and self.picture):
            self._generate_thumbnail()

    def _generate_thumbnail(self):
        from seoto.utils import MediaHelper

        if not self.picture:
            if self.picture_thumbnail:
                self.picture_thumbnail.delete(save=False)
                type(self).objects.filter(pk=self.pk).update(picture_thumbnail='')
            return

        MediaHelper.generate_thumbnail(
            self, 'picture', 'picture_thumbnail',
            f'accounts/thumbs/{self.user.username}_thumb.jpg'
        )

    def __str__(self):
        return f'{self.user.username}'
