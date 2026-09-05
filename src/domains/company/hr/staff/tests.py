from datetime import date

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from domains.company.hr.staff.admin.staff import MemberAdmin
from domains.company.hr.staff.models import Member, StaffIdSequence

User = get_user_model()


def make_member(username, **kwargs):
    user = User.objects.create_user(username=username)
    return Member.objects.create(user=user, started_on=date(2026, 1, 1), **kwargs)


class StaffIdTests(TestCase):
    def test_first_member_starts_the_sequence(self):
        self.assertEqual(make_member('ama').staff_id, 'SEO-0001')

    def test_sequence_increments_per_member(self):
        make_member('ama')
        make_member('kofi')
        self.assertEqual(make_member('yaa').staff_id, 'SEO-0003')

    def test_deleting_a_member_does_not_free_their_number(self):
        make_member('ama')
        make_member('kofi').delete()
        self.assertEqual(make_member('yaa').staff_id, 'SEO-0003')

    def test_id_is_stable_across_saves(self):
        member = make_member('ama')
        member.hometown = 'Kumasi'
        member.save()
        member.refresh_from_db()
        self.assertEqual(member.staff_id, 'SEO-0001')

    def test_field_is_not_editable(self):
        self.assertFalse(Member._meta.get_field('staff_id').editable)

    def test_padding_survives_overflow(self):
        StaffIdSequence.objects.create(last_issued=9999)
        self.assertEqual(make_member('ama').staff_id, 'SEO-10000')

    def test_sequence_row_is_created_on_demand(self):
        self.assertFalse(StaffIdSequence.objects.exists())
        make_member('ama')
        self.assertEqual(StaffIdSequence.objects.get().last_issued, 1)


class MemberAdminTests(TestCase):
    def setUp(self):
        self.admin = MemberAdmin(Member, AdminSite())
        self.request = RequestFactory().get('/')
        self.request.user = User.objects.create_superuser(username='root', password='x')

    def _first_fieldset_fields(self, obj):
        return self.admin.get_fieldsets(self.request, obj)[0][1]['fields']

    def test_add_form_hides_the_id(self):
        self.assertNotIn('staff_id', self._first_fieldset_fields(None))

    def test_change_form_shows_the_id(self):
        member = make_member('ama')
        self.assertIn('staff_id', self._first_fieldset_fields(member))

    def test_change_form_keeps_the_id_readonly(self):
        member = make_member('ama')
        self.assertIn('staff_id', self.admin.get_readonly_fields(self.request, member))

    def test_change_form_cannot_write_the_id(self):
        member = make_member('ama')
        form = self.admin.get_form(self.request, member)()
        self.assertNotIn('staff_id', form.fields)
