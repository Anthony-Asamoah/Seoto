from django.contrib import admin
from django.contrib.admin.widgets import AutocompleteSelectMultiple
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase

from domains.apps.blog.models import PostReadGroup
from domains.apps.spending_tracker.models import Transaction


class AutocompleteManyToManyTests(TestCase):
    """Plain many-to-many fields are autocompletes; unfold ships no tag box of its own."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser('m2m-admin', 'm2m@example.com', 'pw')

    def widget(self, model, field_name):
        request = RequestFactory().get('/admin/')
        request.user = self.user
        form = admin.site._registry[model].get_form(request)()
        widget = form.fields[field_name].widget
        return getattr(widget, 'widget', widget)

    def test_transaction_tags_use_autocomplete(self):
        self.assertIsInstance(self.widget(Transaction, 'tags'), AutocompleteSelectMultiple)

    def test_read_group_users_use_autocomplete(self):
        self.assertIsInstance(self.widget(PostReadGroup, 'users'), AutocompleteSelectMultiple)
