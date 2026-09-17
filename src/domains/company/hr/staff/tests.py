import json
from datetime import date
from decimal import Decimal

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.forms import inlineformset_factory
from django.http import Http404
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from domains.company.hr.staff.admin.staff import MemberAdmin
from domains.company.hr.staff.admin.staff import (
    AssignmentInline,
    AssignmentInlineForm,
    AssignmentInlineFormSet,
    PositionAdmin,
)
from domains.company.hr.staff.models import Assignment, Member, Position, StaffIdSequence

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
        rows = self.admin.get_fieldsets(self.request, obj)[0][1]['fields']
        return [
            field
            for row in rows
            for field in (row if isinstance(row, (list, tuple)) else (row,))
        ]

    def test_the_change_form_is_a_single_fieldset(self):
        member = make_member('ama')
        self.assertEqual(len(self.admin.get_fieldsets(self.request, member)), 1)

    def test_the_single_fieldset_covers_every_editable_field(self):
        member = make_member('ama')
        fields = self._first_fieldset_fields(member)
        for name in ('user', 'started_on', 'gender', 'national_id', 'profile_image', 'is_public'):
            self.assertIn(name, fields)

    def test_the_profile_image_is_croppable(self):
        member = make_member('ama')
        form = self.admin.get_form(self.request, member)()
        self.assertTrue(form.fields['profile_image'].widget.crop)

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



def make_assignment(member, position, effective_from, effective_to=None, salary=1000):
    return Assignment.objects.create(
        member=member, position=position, salary=salary,
        effective_from=effective_from, effective_to=effective_to,
    )


class ConcurrentAssignmentTests(TestCase):
    def setUp(self):
        self.member = make_member('ama')
        self.developer = Position.objects.create(name='Widget Wrangler')
        self.lead = Position.objects.create(name='Widget Lead')

    def test_two_positions_can_start_on_the_same_day(self):
        make_assignment(self.member, self.developer, date(2026, 1, 1))
        make_assignment(self.member, self.lead, date(2026, 1, 1))
        self.assertEqual(self.member.assignments.count(), 2)

    def test_both_open_assignments_are_current(self):
        make_assignment(self.member, self.developer, date(2026, 1, 1))
        make_assignment(self.member, self.lead, date(2026, 3, 1))
        self.assertCountEqual(self.member.positions, [self.developer, self.lead])

    def test_an_ended_assignment_drops_out(self):
        make_assignment(self.member, self.developer, date(2026, 1, 1), date(2026, 2, 1))
        make_assignment(self.member, self.lead, date(2026, 2, 2))
        self.assertEqual(self.member.positions, [self.lead])

    def test_a_future_assignment_is_not_current_yet(self):
        make_assignment(self.member, self.developer, date(2099, 1, 1))
        self.assertEqual(self.member.positions, [])

    def test_the_same_position_cannot_overlap_itself(self):
        make_assignment(self.member, self.developer, date(2026, 1, 1))
        clash = Assignment(
            member=self.member, position=self.developer, salary=2000, effective_from=date(2026, 6, 1)
        )
        with self.assertRaises(ValidationError):
            clash.full_clean()

    def test_a_pay_change_after_the_old_row_ends_is_allowed(self):
        make_assignment(self.member, self.developer, date(2026, 1, 1), date(2026, 5, 31))
        raise_ = Assignment(
            member=self.member, position=self.developer, salary=2000, effective_from=date(2026, 6, 1)
        )
        raise_.full_clean()

    def test_an_end_before_the_start_is_rejected(self):
        assignment = Assignment(
            member=self.member, position=self.developer, salary=1000,
            effective_from=date(2026, 6, 1), effective_to=date(2026, 1, 1),
        )
        with self.assertRaises(ValidationError):
            assignment.full_clean()


class AssignmentInlineFormSetTests(TestCase):
    def setUp(self):
        self.member = make_member('ama')
        self.developer = Position.objects.create(name='Widget Wrangler')

    def _formset(self, rows, instances=()):
        FormSet = inlineformset_factory(
            Member, Assignment, form=AssignmentInlineForm, formset=AssignmentInlineFormSet,
            fields=('position', 'salary', 'currency', 'effective_from', 'effective_to', 'note'), extra=0,
        )
        data = {
            'assignments-TOTAL_FORMS': str(len(rows)),
            'assignments-INITIAL_FORMS': str(len(instances)),
            'assignments-MIN_NUM_FORMS': '0',
            'assignments-MAX_NUM_FORMS': '1000',
        }
        for index, row in enumerate(rows):
            for key, value in row.items():
                data[f'assignments-{index}-{key}'] = value
        return FormSet(data, instance=self.member)

    def _row(self, effective_from, effective_to='', pk=''):
        return {
            'id': pk, 'member': str(self.member.pk), 'position': str(self.developer.pk),
            'salary': '1000', 'currency': 'GHS', 'note': '',
            'effective_from': effective_from, 'effective_to': effective_to,
        }

    def test_overlapping_rows_in_one_submit_are_rejected(self):
        formset = self._formset([self._row('2026-01-01'), self._row('2026-06-01')])
        self.assertFalse(formset.is_valid())
        self.assertIn(Assignment.OVERLAP_ERROR, formset.forms[1].errors['effective_from'])

    def test_ending_a_row_and_replacing_it_in_one_submit_is_allowed(self):
        existing = make_assignment(self.member, self.developer, date(2026, 1, 1))
        formset = self._formset(
            [self._row('2026-01-01', '2026-05-31', pk=str(existing.pk)), self._row('2026-06-01')],
            instances=[existing],
        )
        self.assertTrue(formset.is_valid(), formset.errors)



class AssignmentDefaultsTests(TestCase):
    """built through the admin inline, since the wrapper the admin adds is what broke this"""

    def setUp(self):
        self.member = make_member('ama')
        self.developer = Position.objects.create(
            name='Widget Wrangler', reference_salary=Decimal('4500.00')
        )
        self.inline = AssignmentInline(Member, AdminSite())
        self.request = RequestFactory().get('/')
        self.request.user = User.objects.create_superuser('boss')
        self.expected_url = reverse('admin:company_staff_position_defaults')

    def _formset(self):
        FormSet = self.inline.get_formset(self.request, self.member)
        return FormSet(instance=self.member)

    def test_a_new_row_starts_today(self):
        self.assertEqual(self._formset().empty_form['effective_from'].value(), timezone.localdate())

    def test_a_saved_row_keeps_its_own_date(self):
        make_assignment(self.member, self.developer, date(2026, 1, 1))
        self.assertEqual(self._formset().forms[0]['effective_from'].value(), date(2026, 1, 1))

    def test_the_blank_template_row_advertises_the_defaults_endpoint(self):
        # Asserting on the HTML, not widget.attrs: the admin wraps the select in a
        # RelatedFieldWidgetWrapper whose attrs never reach the rendered tag.
        html = str(self._formset().empty_form['position'])
        self.assertIn(f'data-defaults-url="{self.expected_url}"', html)

    def test_a_saved_row_also_advertises_the_defaults_endpoint(self):
        make_assignment(self.member, self.developer, date(2026, 1, 1))
        html = str(self._formset().forms[0]['position'])
        self.assertIn(f'data-defaults-url="{self.expected_url}"', html)


class PositionDefaultsViewTests(TestCase):
    """the admin site is behind OTP, so drive the view itself rather than the URL"""

    def setUp(self):
        self.admin = PositionAdmin(Position, AdminSite())
        self.factory = RequestFactory()
        self.boss = User.objects.create_superuser('boss')

    def _get(self, position_id, user=None):
        request = self.factory.get('/', {'position': position_id})
        request.user = user or self.boss
        return self.admin.defaults_view(request)

    def test_it_returns_the_reference_figures(self):
        position = Position.objects.create(
            name='Chief Widget Officer', reference_salary=Decimal('4500.00'), currency='USD'
        )
        self.assertEqual(
            json.loads(self._get(position.pk).content), {'salary': '4500.00', 'currency': 'USD'}
        )

    def test_a_position_without_a_reference_salary_returns_blank(self):
        position = Position.objects.create(name='Widget Intern')
        self.assertEqual(json.loads(self._get(position.pk).content)['salary'], '')

    def test_an_unknown_position_is_a_404(self):
        with self.assertRaises(Http404):
            self._get(0)

    def test_a_user_without_the_view_permission_is_refused(self):
        nobody = User.objects.create_user('nobody', is_staff=True)
        position = Position.objects.create(name='Widget Cleaner')
        with self.assertRaises(PermissionDenied):
            self._get(position.pk, user=nobody)

    def test_the_admin_site_route_is_registered(self):
        self.assertTrue(reverse('admin:company_staff_position_defaults'))


from domains.company.hr.staff.models import (
    Certificate,
    Contact,
    ContactChannel,
    Membership,
    MembershipRole,
    Specialisation,
    Team,
)
from domains.company.hr.staff.services import members as member_services


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
