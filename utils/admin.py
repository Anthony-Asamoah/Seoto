from django_ckeditor_5.widgets import CKEditor5Widget


class RichTextAdminMixin:
    """
    Mixin for ModelAdmin classes that replaces plain TextArea widgets with
    CKEditor 5 on the fields listed in ``richtext_fields``.

    Usage::

        class MyModelAdmin(RichTextAdminMixin, admin.ModelAdmin):
            richtext_fields = ('body', 'summary')          # required
            richtext_config = 'blog'                        # optional, defaults to 'default'
    """

    richtext_fields: tuple = ()
    richtext_config: str = 'default'

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        for field_name in self.richtext_fields:
            if field_name in form.base_fields:
                form.base_fields[field_name].widget = CKEditor5Widget(
                    config_name=self.richtext_config
                )
        return form
