from ..models import FAQCategory


def list_published_categories():
    """Categories holding at least one published question, in display order.

    Empty sections are dropped rather than rendered as a heading with nothing
    under it.
    """
    return (
        FAQCategory.objects
        .filter(faqs__is_published=True)
        .order_by('order', 'name')
        .distinct()
    )
