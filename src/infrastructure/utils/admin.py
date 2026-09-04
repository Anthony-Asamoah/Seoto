from django.contrib.admin.options import BaseModelAdmin
from django_ckeditor_5.widgets import CKEditor5Widget

from infrastructure.utils.widgets import Select2MultipleWidget


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


def install_select2_m2m():
    """Make every admin many-to-many field render as a select2 tag box.

    Patches `BaseModelAdmin`, so it covers `ModelAdmin` and inlines alike without any
    per-admin opt-in. `autocomplete_fields` and `raw_id_fields` are left alone (both are
    deliberate choices for large tables), as is any field listed in a ModelAdmin's
    `select2_exclude`, which falls back to whatever Django would have rendered —
    `filter_horizontal` included.
    """
    if getattr(BaseModelAdmin, '_select2_m2m_installed', False):
        return

    original = BaseModelAdmin.formfield_for_manytomany

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        overridable = (
            'widget' not in kwargs
            and db_field.name not in self.get_autocomplete_fields(request)
            and db_field.name not in self.raw_id_fields
            and db_field.name not in getattr(self, 'select2_exclude', ())
        )
        if overridable:
            kwargs['widget'] = Select2MultipleWidget(
                placeholder=f'Select {db_field.verbose_name}'
            )

        form_field = original(self, db_field, request, **kwargs)

        # Django appends "Hold down Control…" to any SelectMultiple; select2 makes it a lie.
        if overridable and form_field is not None:
            form_field.help_text = db_field.help_text
        return form_field

    BaseModelAdmin.formfield_for_manytomany = formfield_for_manytomany
    BaseModelAdmin.select2_exclude = ()
    BaseModelAdmin._select2_m2m_installed = True
