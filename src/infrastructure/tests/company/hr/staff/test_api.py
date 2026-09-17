import json
from datetime import date

from django.test import TestCase
from django.urls import reverse

from domains.company.hr.staff.models import (
    Assignment, Member, Position, Certificate, Contact, ContactChannel, Membership, MembershipRole,
    Specialisation, Team,
)

from .helpers import User, make_assignment


class MemberApiTests(TestCase):
    """the public directory — what it exposes matters as much as what it filters"""

    @classmethod
    def setUpTestData(cls):
        cls.developer = Position.objects.create(name='Widget Wrangler')
        cls.designer = Position.objects.create(name='Widget Designer')
        cls.core = Team.objects.create(name='Core')
        cls.labs = Team.objects.create(name='Labs')

        cls.ama = cls._member('ama', 'Ama', 'Mensah', is_public=True, nationality='Ghanaian')
        make_assignment(cls.ama, cls.developer, date(2026, 1, 1))
        Membership.objects.create(
            team=cls.core, member=cls.ama, role=MembershipRole.LEAD, joined_on=date(2026, 1, 1)
        )
        Specialisation.objects.create(member=cls.ama, name='Django')
        Contact.objects.create(
            member=cls.ama, channel=ContactChannel.EMAIL,
            value='ama@example.com', is_public=True,
        )
        Contact.objects.create(
            member=cls.ama, channel=ContactChannel.MOBILE, value='+233244000000',
        )

        cls.kofi = cls._member('kofi', 'Kofi', 'Owusu', is_public=True, nationality='Nigerian')
        make_assignment(cls.kofi, cls.designer, date(2026, 2, 1))
        Membership.objects.create(team=cls.labs, member=cls.kofi, joined_on=date(2026, 2, 1))

        cls.hidden = cls._member('yaa', 'Yaa', 'Boateng', is_public=False)

    @classmethod
    def _member(cls, username, first, last, **kwargs):
        user = User.objects.create_user(username=username, first_name=first, last_name=last)
        return Member.objects.create(user=user, started_on=date(2026, 1, 1), **kwargs)

    def _ids(self, **params):
        response = self.client.get(reverse('member_list'), params)
        self.assertEqual(response.status_code, 200, response.content)
        return [row['staff_id'] for row in response.json()['results']]

    def test_only_public_members_are_listed(self):
        self.assertCountEqual(self._ids(), [self.ama.staff_id, self.kofi.staff_id])

    def test_the_card_never_leaks_private_columns(self):
        row = self.client.get(reverse('member_list')).json()['results'][0]
        for field in ('national_id', 'date_of_birth', 'salary', 'user'):
            self.assertNotIn(field, row)

    def test_the_detail_never_leaks_salary(self):
        response = self.client.get(reverse('member_detail', args=[self.ama.staff_id]))
        self.assertNotIn('salary', json.dumps(response.json()))

    def test_a_private_member_is_a_404(self):
        response = self.client.get(reverse('member_detail', args=[self.hidden.staff_id]))
        self.assertEqual(response.status_code, 404)

    def test_only_public_contacts_are_returned(self):
        response = self.client.get(reverse('member_detail', args=[self.ama.staff_id]))
        self.assertEqual(
            [c['value'] for c in response.json()['contacts']], ['ama@example.com']
        )

    def test_filter_by_position(self):
        self.assertEqual(self._ids(position='widget wrangler'), [self.ama.staff_id])

    def test_a_past_assignment_does_not_match_the_position_filter(self):
        Assignment.objects.filter(member=self.kofi).update(effective_to=date(2026, 2, 2))
        self.assertEqual(self._ids(position='widget designer'), [])

    def test_filter_by_team(self):
        self.assertEqual(self._ids(team='Labs'), [self.kofi.staff_id])

    def test_filter_by_role(self):
        self.assertEqual(self._ids(role='lead'), [self.ama.staff_id])

    def test_filter_by_specialisation(self):
        self.assertEqual(self._ids(specialisation='django'), [self.ama.staff_id])

    def test_a_hidden_specialisation_does_not_match(self):
        Specialisation.objects.filter(member=self.ama).update(hidden=True)
        self.assertEqual(self._ids(specialisation='django'), [])

    def test_repeating_a_param_requires_every_value(self):
        self.assertEqual(self._ids(team=['Core', 'Labs']), [])

    def test_filter_by_nationality_is_case_insensitive_contains(self):
        self.assertEqual(self._ids(nationality='ghana'), [self.ama.staff_id])

    def test_search_covers_name_and_position(self):
        self.assertEqual(self._ids(q='Owusu'), [self.kofi.staff_id])
        self.assertEqual(self._ids(q='Wrangler'), [self.ama.staff_id])

    def test_filter_by_certificate(self):
        Certificate.objects.create(
            member=self.kofi, course_name='Widget Safety', issuing_body='ISO'
        )
        self.assertEqual(self._ids(certificate='widget safety'), [self.kofi.staff_id])

    def test_former_members_are_excluded_by_is_active(self):
        Member.objects.filter(pk=self.kofi.pk).update(ended_on=date(2026, 6, 1))
        self.assertEqual(self._ids(is_active='true'), [self.ama.staff_id])
        self.assertEqual(self._ids(is_active='false'), [self.kofi.staff_id])

    def test_ordering_by_name_does_not_expose_the_user_join(self):
        self.assertEqual(
            self._ids(ordering='-name'), [self.kofi.staff_id, self.ama.staff_id]
        )

    def test_an_unknown_ordering_field_is_a_400(self):
        response = self.client.get(reverse('member_list'), {'ordering': 'salary'})
        self.assertEqual(response.status_code, 400)

    def test_an_unknown_role_is_a_400(self):
        self.assertEqual(self.client.get(reverse('member_list'), {'role': 'boss'}).status_code, 400)

    def test_a_malformed_date_is_a_400_not_a_500(self):
        response = self.client.get(reverse('member_list'), {'started_after': 'yesterday'})
        self.assertEqual(response.status_code, 400)

    def test_joins_do_not_duplicate_rows(self):
        Specialisation.objects.create(member=self.ama, name='Postgres')
        make_assignment(self.ama, self.designer, date(2026, 3, 1))
        self.assertEqual(self._ids(q='Ama'), [self.ama.staff_id])

    def test_the_list_does_not_query_per_row(self):
        # The prefetches in the service are the only thing keeping this flat;
        # asserting against a third member, not a literal, is what proves it.
        with self.assertNumQueries(5):
            self.client.get(reverse('member_list'))

        extra = self._member('abena', 'Abena', 'Asante', is_public=True)
        make_assignment(extra, self.developer, date(2026, 4, 1))
        Specialisation.objects.create(member=extra, name='Rust')
        with self.assertNumQueries(5):
            self.client.get(reverse('member_list'))

    def test_facets_only_offer_values_a_public_member_carries(self):
        facets = self.client.get(reverse('member_facet_list')).json()
        self.assertCountEqual(facets['positions'], ['Widget Wrangler', 'Widget Designer'])
        self.assertCountEqual(facets['teams'], ['Core', 'Labs'])
        self.assertEqual(facets['specialisations'], ['Django'])
