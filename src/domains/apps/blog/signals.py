import logging
import re
from urllib.parse import urlparse

from django.conf import settings
from django.core.files.storage import default_storage
from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import Post

logger = logging.getLogger(__name__)

_BLOG_MEDIA_PREFIXES = ('blog/images/', 'blog/media/')


def _url_to_storage_path(url):
    """Convert a media URL embedded in post content to a storage-relative path.
    Returns None if the URL cannot be mapped to a known storage path.
    """
    media_url = settings.MEDIA_URL
    file_path = urlparse(url).path.lstrip('/')
    media_path_prefix = urlparse(media_url).path.lstrip('/')

    if media_path_prefix and file_path.startswith(media_path_prefix):
        return file_path[len(media_path_prefix):]

    # Fallback: extract known blog storage segments (handles S3 presigned URLs)
    for prefix in _BLOG_MEDIA_PREFIXES:
        if prefix in file_path:
            return prefix + file_path.split(prefix)[-1]

    return None


@receiver(post_delete, sender=Post)
def delete_post_media(sender, instance, **kwargs):
    """Delete media files embedded in a post's content when the post is deleted."""
    if not instance.content:
        return

    # Match src/href on img, source, iframe, and anchor tags
    urls = re.findall(r'<(?:img|source|iframe|a)[^>]+(?:src|href)=["\']([^"\']+)["\']', instance.content)
    for url in urls:
        storage_path = _url_to_storage_path(url)
        if not storage_path:
            continue
        try:
            if default_storage.exists(storage_path):
                default_storage.delete(storage_path)
                logger.info(f'Deleted blog media file: {storage_path}')
        except Exception as e:
            logger.warning(f'Failed to delete blog media file {storage_path}: {e}')
