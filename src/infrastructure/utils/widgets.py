from django import forms
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe


class Select2MultipleWidget(forms.SelectMultiple):
    """A plain multi-select carrying select2's HTML5 options as data attributes.

    jazzmin's `change_form.js` already calls `.select2()` on every select it hasn't
    excluded, and select2 merges `data-*` attributes into its options, so the tag
    editor needs no JavaScript of its own.
    """

    def __init__(self, attrs=None, choices=(), placeholder=''):
        defaults = {
            'class': 'admin-select2',
            'data-placeholder': placeholder or 'Start typing to search…',
            'data-allow-clear': 'true',
            'data-close-on-select': 'false',
            'data-width': '100%',
        }
        defaults.update(attrs or {})
        super().__init__(defaults, choices)


class ImagePreviewInput(forms.ClearableFileInput):
    """File input that shows the current image as a thumbnail opening a modal, not a URL.

    Rendered in Python rather than a template: the form renderer runs on its own
    isolated engine, which never sees `SRC_DIR/templates`.
    """

    class Media:
        js = ('js/admin_image_preview.js',)

    thumbnail_url = None

    def __init__(self, attrs=None, crop=False):
        self.crop = crop
        super().__init__(attrs)

    def render(self, name, value, attrs=None, renderer=None):
        has_image = self.is_initial(value)
        attrs = {**(attrs or {}), 'class': 'image-preview-file'}
        file_input = forms.FileInput(self.attrs).render(name, None, attrs, renderer)
        input_id = attrs.get('id', f'id_{name}')
        image_url = value.url if has_image else ''

        parts = [format_html(
            '<img class="image-preview-thumb image-preview-trigger" src="{}" data-image-url="{}" alt=""{}>',
            self.thumbnail_url or image_url, image_url,
            mark_safe('' if has_image else ' hidden'),
        ), file_input]

        buttons = [format_html(
            '<button type="button" class="btn btn-sm btn-outline-secondary image-preview-trigger"'
            ' data-image-url="{}"{}><i class="fas fa-eye"></i> Preview</button>',
            image_url, mark_safe('' if has_image else ' hidden'),
        ), format_html(
            '<button type="button" class="btn btn-sm btn-outline-secondary image-preview-upload"'
            ' data-target="{}"><i class="fas fa-upload"></i> Upload</button>',
            input_id,
        )]
        if has_image and not self.is_required:
            checkbox_id = self.clear_checkbox_id(self.clear_checkbox_name(name))
            buttons.append(format_html(
                '<input type="checkbox" class="image-preview-clear-input" name="{}" id="{}" hidden>'
                '<button type="button" class="btn btn-sm btn-outline-danger image-preview-remove"'
                ' data-target="{}"><i class="fas fa-trash"></i> Remove</button>',
                self.clear_checkbox_name(name), checkbox_id, checkbox_id,
            ))

        parts.append(format_html(
            '<div class="image-preview-actions">{}</div>',
            format_html_join('', '{}', ((b,) for b in buttons)),
        ))
        parts.append(mark_safe('<span class="image-preview-status"></span>'))
        return format_html(
            '<div class="image-preview-widget"{}>{}</div>',
            mark_safe(' data-crop="square"' if self.crop else ''),
            format_html_join('', '{}', ((p,) for p in parts)),
        )
