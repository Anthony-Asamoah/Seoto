import logging
from functools import partial

from django.contrib.auth.models import User
from django.core.files.uploadedfile import UploadedFile
from django.db import models

from accounts.utils import user_directory_file_path

logger = logging.getLogger(__name__)


class user_profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    contact = models.CharField(max_length=15, null=True, blank=True)
    picture = models.ImageField(
        upload_to=partial(user_directory_file_path, prefix='accounts/%Y-%m-%d'),
        blank=True, null=True
    )
    picture_thumbnail = models.ImageField(upload_to='accounts/thumbs', blank=True, null=True)

    def save(self, *args, **kwargs):
        new_picture = isinstance(self.picture, UploadedFile)
        first_save = not self.pk
        super().save(*args, **kwargs)
        if new_picture or (first_save and self.picture):
            self._generate_thumbnail()

    def _generate_thumbnail(self):
        from io import BytesIO
        from PIL import Image
        from django.core.files.base import ContentFile

        if not self.picture:
            if self.picture_thumbnail:
                self.picture_thumbnail.delete(save=False)
                type(self).objects.filter(pk=self.pk).update(picture_thumbnail='')
            return

        # Delete old thumbnail first, independently of new generation
        if self.picture_thumbnail:
            try:
                self.picture_thumbnail.delete(save=False)
            except Exception:
                logger.warning('Failed to delete old thumbnail for %s', self.user.username)

        try:
            self.picture.open('rb')
            img = Image.open(self.picture)
            img.load()

            w, h = img.size
            d = min(w, h)
            img = img.crop(((w - d) // 2, (h - d) // 2, (w + d) // 2, (h + d) // 2))
            img = img.resize((80, 80), Image.LANCZOS)

            if img.mode in ('RGBA', 'P', 'LA'):
                img = img.convert('RGB')

            buf = BytesIO()
            img.save(buf, format='JPEG', quality=85, optimize=True)
            buf.seek(0)

            thumb_name = f'accounts/thumbs/{self.user.username}_thumb.jpg'
            self.picture_thumbnail.save(thumb_name, ContentFile(buf.getvalue()), save=False)
            type(self).objects.filter(pk=self.pk).update(
                picture_thumbnail=self.picture_thumbnail.name
            )
        except Exception:
            logger.exception('Failed to generate thumbnail for %s', self.user.username)
            type(self).objects.filter(pk=self.pk).update(picture_thumbnail='')
        finally:
            try:
                self.picture.close()
            except Exception:
                pass

    def __str__(self):
        return f'{self.user.username}'
