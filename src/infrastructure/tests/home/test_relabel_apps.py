from unittest import mock

from django.db import connection
from django.test import TransactionTestCase

from domains.home.services import relabel_apps


class RelabelAppsTests(TransactionTestCase):
    def run_relabel(self, renames):
        messages = []
        relabel_apps(renames, on_progress=lambda message, level='info': messages.append(message))
        return messages

    def test_a_fresh_database_is_a_no_op(self):
        with mock.patch.object(connection.introspection, 'table_names', return_value=[]):
            messages = self.run_relabel({'old_label': 'new_label'})

        self.assertEqual(messages, ['fresh database: nothing to relabel'])

    def test_a_label_with_no_migration_history_is_skipped(self):
        messages = self.run_relabel({'never_installed': 'new_label'})

        self.assertEqual(messages, ['never_installed: nothing to relabel'])
