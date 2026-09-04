from django import forms


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
