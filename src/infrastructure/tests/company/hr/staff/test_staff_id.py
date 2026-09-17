from django.test import TestCase

from domains.company.hr.staff.models import Member, StaffIdSequence

from .helpers import make_member


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
