from django.db.models import Prefetch, Q

from ..models import Product, ProductImage, ProductStatus

# Drafts stay private; everything else is public.
PUBLIC_STATUSES = [s.name for s in ProductStatus if s is not ProductStatus.DRAFT]

# An open ordering param lets callers sort by columns we never meant to expose.
ORDERING_FIELDS = {
    'order', 'title', 'launched_on', 'created_at', 'updated_at', 'status',
    'is_featured',
}


class ProductFilterError(ValueError):
    """A filter value the caller got wrong; the API turns this into a 400."""


def published_products():
    """Public products with tags and images prefetched in display order."""
    return (
        Product.objects
        .filter(status__in=PUBLIC_STATUSES)
        .prefetch_related(
            'tags',
            Prefetch('images', queryset=ProductImage.objects.order_by('order')),
        )
    )


def get_published_product(slug):
    """One public product, or ``None``."""
    return published_products().filter(slug=slug).first()


def list_published_products(
    *, tags=None, statuses=None, client=None, search=None,
    launched_after=None, launched_before=None, has_images=None,
    is_featured=None, ordering=None,
):
    """Public products narrowed by the listings-page filters, AND-ed together.

    Raises ``ProductFilterError`` for a value the caller got wrong.
    """
    queryset = published_products()

    for tag in tags or []:
        # Chained, not ``label__in``: "has all of these tags", not "has any".
        queryset = queryset.filter(tags__label__iexact=tag)

    statuses = [s.upper() for s in statuses or []]
    if statuses:
        unknown = [s for s in statuses if s not in PUBLIC_STATUSES]
        if unknown: raise ProductFilterError(
            f"Unknown status: {', '.join(unknown)}. "
            f"Allowed: {', '.join(PUBLIC_STATUSES)}."
        )
        queryset = queryset.filter(status__in=statuses)

    if client:
        queryset = queryset.filter(client__icontains=client)

    if search: queryset = queryset.filter(
        Q(title__icontains=search)
        | Q(client__icontains=search)
        | Q(summary__icontains=search)
        | Q(body__icontains=search)
    )

    if launched_after:
        queryset = queryset.filter(launched_on__gte=launched_after)

    if launched_before:
        queryset = queryset.filter(launched_on__lte=launched_before)

    if has_images is not None:
        queryset = queryset.filter(
            images__isnull=not _parse_bool(has_images, 'has_images')
        )

    if is_featured is not None:
        queryset = queryset.filter(
            is_featured=_parse_bool(is_featured, 'is_featured')
        )

    if ordering:
        if ordering.lstrip('-') not in ORDERING_FIELDS:
            raise ProductFilterError(
                f"Cannot order by '{ordering}'. "
                f"Allowed: {', '.join(sorted(ORDERING_FIELDS))}."
            )
        queryset = queryset.order_by(ordering)

    # Joins across tags/images duplicate rows, so page counts would lie.
    return queryset.distinct()


def _parse_bool(value, name):
    if value.lower() in ('true', '1'): return True
    if value.lower() in ('false', '0'): return False
    raise ProductFilterError(f'{name} must be true or false.')
