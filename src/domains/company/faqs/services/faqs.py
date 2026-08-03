from django.db.models import Q

from ..models import FAQ

# An open ordering param lets callers sort by columns we never meant to expose.
ORDERING_FIELDS = {
    'order', 'question', 'created_at', 'updated_at', 'is_featured',
}


class FAQFilterError(ValueError):
    """A filter value the caller got wrong; the API turns this into a 400."""


def published_faqs():
    """Public questions with their category joined, in display order."""
    return FAQ.objects.filter(is_published=True).select_related('category')


def get_published_faq(slug):
    """One public question, or ``None``."""
    return published_faqs().filter(slug=slug).first()


def list_published_faqs(*, categories=None, search=None, is_featured=None, ordering=None):
    """Public questions narrowed by the FAQ-page filters, AND-ed together.

    Raises ``FAQFilterError`` for a value the caller got wrong.
    """
    queryset = published_faqs()

    categories = [c for c in categories or [] if c]
    if categories:
        # "in any of these sections", unlike the products tag filter — a
        # question belongs to exactly one category, so AND-ing would return
        # nothing.
        queryset = queryset.filter(category__slug__in=categories)

    if search: queryset = queryset.filter(
        Q(question__icontains=search) | Q(answer__icontains=search)
    )

    if is_featured is not None:
        queryset = queryset.filter(
            is_featured=_parse_bool(is_featured, 'is_featured')
        )

    if ordering:
        if ordering.lstrip('-') not in ORDERING_FIELDS:
            raise FAQFilterError(
                f"Cannot order by '{ordering}'. "
                f"Allowed: {', '.join(sorted(ORDERING_FIELDS))}."
            )
        queryset = queryset.order_by(ordering)

    return queryset


def schema_faqs():
    """The questions eligible for the FAQPage JSON-LD."""
    return published_faqs().filter(include_in_schema=True)


def _parse_bool(value, name):
    if value.lower() in ('true', '1'): return True
    if value.lower() in ('false', '0'): return False
    raise FAQFilterError(f'{name} must be true or false.')
