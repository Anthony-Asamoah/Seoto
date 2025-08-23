from django.core.paginator import Paginator


def apply_pagination(data, page_number, per_page):
    paginator = Paginator(data, per_page)
    page_obj = paginator.get_page(page_number)
    return page_obj
