from django.contrib import admin
from django.contrib.admin.widgets import AutocompleteSelectMultiple, FilteredSelectMultiple
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase

from domains.apps.blog.models import Post
from domains.apps.spending_tracker.models import Transaction
from infrastructure.utils import Select2MultipleWidget


class Select2ManyToManyTests(TestCase):
    """The site-wide select2 M2M widget installed by `install_select2_m2m`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser('m2m-admin', 'm2m@example.com', 'pw')

    def form_field(self, model, field_name, admin_class=None):
        request = RequestFactory().get('/admin/')
        request.user = self.user
        model_admin = (admin_class or admin.site._registry[model].__class__)(model, admin.site)
        return model_admin.get_form(request)().fields[field_name]

    def widget(self, *args, **kwargs):
        field = self.form_field(*args, **kwargs)
        return getattr(field.widget, 'widget', field.widget)

    def test_a_plain_m2m_field_renders_as_select2(self):
        widget = self.widget(Transaction, 'tags')

        self.assertIsInstance(widget, Select2MultipleWidget)
        self.assertEqual(widget.attrs['class'], 'admin-select2')
        self.assertEqual(widget.attrs['data-placeholder'], 'Select tags')

    def test_the_hold_down_control_help_text_is_dropped(self):
        self.assertEqual(self.form_field(Transaction, 'tags').help_text, '')

    def test_autocomplete_fields_keep_their_own_widget(self):
        self.assertIsInstance(self.widget(Post, 'tags'), AutocompleteSelectMultiple)

    def test_select2_exclude_falls_back_to_django(self):
        class ExcludedAdmin(admin.ModelAdmin):
            select2_exclude = ('tags',)
            filter_horizontal = ('tags',)

        widget = self.widget(Transaction, 'tags', admin_class=ExcludedAdmin)

        self.assertIsInstance(widget, FilteredSelectMultiple)
