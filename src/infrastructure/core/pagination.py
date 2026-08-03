from django.conf import settings
from django.core.paginator import Paginator
from rest_framework.pagination import PageNumberPagination


class DefaultAPIPagination(PageNumberPagination):
    """Page-number pagination shared by the public API. Sizes bind at import
    time, so changing the env needs a restart."""

    page_size = settings.API_PAGE_SIZE
    page_size_query_param = 'page_size'
    max_page_size = settings.API_MAX_PAGE_SIZE


def apply_view_pagination(data, page_number, per_page = 5):
    paginator = Paginator(data, per_page)
    page_obj = paginator.get_page(page_number)
    return page_obj
