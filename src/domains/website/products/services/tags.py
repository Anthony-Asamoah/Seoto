from ..models import Product
from .products import PUBLIC_STATUSES


def list_published_tag_labels():
    """Every tag label carried by a published product, in display order."""
    return list(
        Product.objects
        .filter(status__in=PUBLIC_STATUSES)
        .values_list('tags__label', flat=True)
        .exclude(tags__label__isnull=True)
        .order_by('tags__order', 'tags__label')
        .distinct()
    )
