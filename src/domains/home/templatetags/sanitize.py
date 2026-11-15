import nh3
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

_MEDIA_TAGS = nh3.ALLOWED_TAGS | {'video', 'audio', 'source', 'iframe'}
_MEDIA_ATTRS = {tag: set(attrs) for tag, attrs in nh3.ALLOWED_ATTRIBUTES.items()}
_MEDIA_ATTRS['*'] = _MEDIA_ATTRS.get('*', set()) | {'style', 'class'}
_MEDIA_ATTRS.update({
    'video': {'src', 'controls', 'preload', 'poster', 'width', 'height'},
    'audio': {'src', 'controls', 'preload'},
    'source': {'src', 'type'},
    'iframe': {'src', 'width', 'height', 'allowfullscreen', 'frameborder'},
})


def _https_only(tag, attr, value):
    if attr in ('src', 'poster') and not value.lower().startswith(('https://', '/')):
        return None
    return value


@register.filter
def sanitize(value):
    return mark_safe(nh3.clean(value or ''))


@register.filter
def sanitize_rich(value):
    return mark_safe(nh3.clean(
        value or '', tags=_MEDIA_TAGS, attributes=_MEDIA_ATTRS, attribute_filter=_https_only,
    ))
