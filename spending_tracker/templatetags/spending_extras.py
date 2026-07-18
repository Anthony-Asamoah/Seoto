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


@register.filter
def humanize_amount(value):
    """
    Formats a currency amount for compact display, abbreviating with K/M/B
    once the magnitude reaches 1000 (e.g. 7800 -> "7.8K", 2300000 -> "2.3M").
    Values under 1000 keep the standard two-decimal display (e.g. "588.00").
    """
    try:
        value = float(value)
    except (TypeError, ValueError):
        return value

    sign = '-' if value < 0 else ''
    magnitude = abs(value)

    if magnitude < 1000:
        return f'{sign}{magnitude:.2f}'

    for divisor, suffix in ((1_000_000_000, 'B'), (1_000_000, 'M'), (1_000, 'K')):
        if magnitude >= divisor:
            scaled = f'{magnitude / divisor:.2f}'.rstrip('0').rstrip('.')
            return f'{sign}{scaled}{suffix}'

    return f'{sign}{magnitude:.2f}'
