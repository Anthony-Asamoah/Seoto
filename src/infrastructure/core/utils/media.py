class MediaHelper:

    @staticmethod
    def generate_thumbnail(instance, image_attr, thumb_attr, thumb_name):
        """Crop, resize to 80x80 JPEG, and save as thumbnail.

        Args:
            instance: model instance
            image_attr: name of the source image field on instance
            thumb_attr: name of the thumbnail field on instance
            thumb_name: storage path for the generated thumbnail
        """
        from io import BytesIO
        from PIL import Image
        from django.core.files.base import ContentFile

        image = getattr(instance, image_attr)
        thumb = getattr(instance, thumb_attr)

        if thumb:
            try:
                thumb.delete(save=False)
            except Exception:
                pass

        try:
            image.open('rb')
            img = Image.open(image)
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

            thumb.save(thumb_name, ContentFile(buf.getvalue()), save=False)
            type(instance).objects.filter(pk=instance.pk).update(
                **{thumb_attr: getattr(instance, thumb_attr).name}
            )
        except Exception:
            type(instance).objects.filter(pk=instance.pk).update(**{thumb_attr: ''})
        finally:
            try:
                image.close()
            except Exception:
                pass
