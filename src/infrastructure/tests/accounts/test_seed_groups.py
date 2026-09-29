import json
from pathlib import Path

from django.contrib.auth.models import Group
from django.test import TestCase

UNITS = [
    'website', 'website.products', 'website.faqs', 'company', 'company.hr.staff',
    'blog', 'foodie', 'jotter', 'rhymes', 'spending_tracker', 'pwa', 'theme', 'accounts', 'home',
]
ROLES = ['viewer', 'editor', 'admin', 'supervisor']


def codes(group_name):
    group = Group.objects.get(name=group_name)
    return set(group.permissions.values_list('content_type__app_label', 'codename'))


class SeedGroupsTests(TestCase):
    def test_every_unit_has_all_roles(self):
        names = set(Group.objects.values_list('name', flat=True))
        self.assertEqual(names, {f'{u}:{r}' for u in UNITS for r in ROLES})

    def test_role_hierarchy(self):
        for unit in UNITS:
            viewer, editor, admin = (codes(f'{unit}:{r}') for r in ('viewer', 'editor', 'admin'))
            self.assertTrue(viewer < editor < admin, unit)

    def test_only_admin_deletes(self):
        for unit in UNITS:
            for role in ('viewer', 'editor', 'supervisor'):
                self.assertFalse([c for _, c in codes(f'{unit}:{role}') if c.startswith('delete_')], (unit, role))
            self.assertTrue([c for _, c in codes(f'{unit}:admin') if c.startswith('delete_')], unit)

    def test_view_all_sits_on_supervisor_and_admin_only(self):
        for unit in ('blog', 'spending_tracker', 'foodie'):
            for role in ('viewer', 'editor'):
                self.assertFalse([c for _, c in codes(f'{unit}:{role}') if c.startswith('view_all_')], (unit, role))
            supervisor = codes(f'{unit}:supervisor')
            self.assertTrue([c for _, c in supervisor if c.startswith('view_all_')], unit)
            self.assertEqual(
                {c for _, c in supervisor if not c.startswith('view_all_')},
                {c for _, c in codes(f'{unit}:viewer')},
            )
            self.assertTrue(supervisor < codes(f'{unit}:admin'))

    def test_ownerless_units_have_no_view_all(self):
        for unit in ('website', 'company.hr.staff', 'home', 'accounts'):
            for role in ROLES:
                self.assertFalse([c for _, c in codes(f'{unit}:{role}') if c.startswith('view_all_')], (unit, role))

    def test_domain_holds_union_of_subdomains(self):
        for role in ROLES:
            union = codes(f'website.products:{role}') | codes(f'website.faqs:{role}')
            self.assertEqual(codes(f'website:{role}'), union)

    def test_fixture_matches_database(self):
        fixture = Path(__file__).resolve().parents[3] / 'domains' / 'accounts' / 'fixtures' / 'groups.json'
        for entry in json.loads(fixture.read_text()):
            expected = {(app, code) for code, app, _ in entry['fields']['permissions']}
            self.assertEqual(codes(entry['fields']['name']), expected)
