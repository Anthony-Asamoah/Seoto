from django.conf import settings
from rest_framework.pagination import PageNumberPagination


class DefaultPagination(PageNumberPagination):
    """Page-number pagination shared by the public API. Sizes bind at import
    time, so changing the env needs a restart."""

    page_size = settings.API_PAGE_SIZE
    page_size_query_param = 'page_size'
    max_page_size = settings.API_MAX_PAGE_SIZE
