from django import template
from django.utils import timezone

register = template.Library()


@register.filter
def relative_date(value):
    """
    Returns a human-readable relative date label for a datetime value:
      Today → "Today"
      1 day ago → "Yesterday"
      2-3 days ago → "2 days ago" / "3 days ago"
      4-7 days ago → "Last week"
      Older → "3 Mar 2026"
    """
    if not value:
        return ''
    today = timezone.localdate()
    try:
        tx_date = timezone.localtime(value).date()
    except Exception:
        tx_date = value
    delta = (today - tx_date).days
    if delta == 0:
        return 'Today'
    elif delta == 1:
        return 'Yesterday'
    elif delta <= 3:
        return f'{delta} days ago'
    elif delta <= 7:
        return 'Last week'
    else:
        return f'{value.day} {value.strftime("%b %Y")}'  # "3 Mar 2026"
