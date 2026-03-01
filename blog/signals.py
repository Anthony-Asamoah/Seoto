import logging
import re
from urllib.parse import urlparse

from django.conf import settings
from django.core.files.storage import default_storage
from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import Post

logger = logging.getLogger(__name__)


def _url_to_storage_path(url):
    """Convert an image URL embedded in post content to a storage-relative path.
    Returns None if the URL cannot be mapped to a known storage path.
    """
    media_url = settings.MEDIA_URL
    img_path = urlparse(url).path.lstrip('/')
    media_path_prefix = urlparse(media_url).path.lstrip('/')

    if media_path_prefix and img_path.startswith(media_path_prefix):
        return img_path[len(media_path_prefix):]

    # Fallback: pull out the blog/images/ segment directly (handles S3 presigned URLs)
    if 'blog/images/' in img_path:
        return 'blog/images/' + img_path.split('blog/images/')[-1]

    return None


@receiver(post_delete, sender=Post)
def delete_post_images(sender, instance, **kwargs):
    """Delete images embedded in a post's content when the post is deleted."""
    if not instance.content:
        return

    urls = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', instance.content)
    for url in urls:
        storage_path = _url_to_storage_path(url)
        if not storage_path:
            continue
        try:
            if default_storage.exists(storage_path):
                default_storage.delete(storage_path)
                logger.info(f'Deleted orphaned blog image: {storage_path}')
        except Exception as e:
            logger.warning(f'Failed to delete blog image {storage_path}: {e}')
