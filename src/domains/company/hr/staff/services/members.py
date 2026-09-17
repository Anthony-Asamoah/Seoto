from datetime import date

from django.db.models import Prefetch, Q
from django.utils import timezone

from ..models import (
    Assignment,
    Certificate,
    Contact,
    Education,
    GenderChoices,
    Hobby,
    JobExperience,
    Member,
    Membership,
    MembershipRole,
    Specialisation,
)

GENDERS = [g.value for g in GenderChoices]
ROLES = [r.value for r in MembershipRole]

# Friendly token -> the columns it really sorts by, so the query params never
# leak the user join or let a caller sort by salary through an assignment.
ORDERING_FIELDS = {
    'name': ('user__first_name', 'user__last_name'),
    'staff_id': ('staff_id',),
    'started_on': ('started_on',),
    'ended_on': ('ended_on',),
}


class MemberFilterError(ValueError):
    """A filter value the caller got wrong; the API turns this into a 400."""


def _public_prefetches(*, detail=False):
    prefetches = [
        Prefetch(
            'assignments',
            queryset=Assignment.objects.current().select_related('position'),
            to_attr='active_assignments',
        ),
        Prefetch(
            'memberships',
            queryset=Membership.objects.active().select_related('team'),
            to_attr='active_memberships',
        ),
        Prefetch(
            'specialisations',
            queryset=Specialisation.objects.filter(hidden=False, is_active=True),
            to_attr='public_specialisations',
        ),
    ]
    if not detail:
        return prefetches

    return prefetches + [
        Prefetch(
            'contacts',
            queryset=Contact.objects.filter(is_public=True, is_active=True),
            to_attr='public_contacts',
        ),
        Prefetch(
            'education',
            queryset=Education.objects.filter(hidden=False),
            to_attr='public_education',
        ),
        Prefetch(
            'certificates',
            queryset=Certificate.objects.filter(hidden=False),
            to_attr='public_certificates',
        ),
        Prefetch(
            'job_experience',
            queryset=JobExperience.objects.filter(hidden=False),
            to_attr='public_job_experience',
        ),
        Prefetch(
            'hobbies',
            queryset=Hobby.objects.filter(hidden=False),
            to_attr='public_hobbies',
        ),
    ]


def public_members(*, detail=False):
    """Members who opted into the public site, with their public relations loaded."""
    return (
        Member.objects
        .filter(is_public=True)
        .select_related('user')
        .prefetch_related(*_public_prefetches(detail=detail))
    )


def get_public_member(staff_id):
    """One public member by staff ID, or ``None``."""
    return public_members(detail=True).filter(staff_id__iexact=staff_id).first()


def list_public_members(
    *, positions=None, teams=None, specialisations=None, roles=None,
    genders=None, nationality=None, hometown=None, school=None,
    certificate=None, search=None, started_after=None, started_before=None,
    is_active=None, has_image=None, ordering=None,
):
    """Public members narrowed by the team-page filters, AND-ed together.

    Raises ``MemberFilterError`` for a value the caller got wrong.
    """
    queryset = public_members()
    today = timezone.localdate()

    # Chained, not ``__in``: repeating a param means "all of these", not "any".
    for position in positions or []:
        # One filter() call, so every condition binds to the same assignment row.
        queryset = queryset.filter(
            Q(assignments__position__name__iexact=position),
            Q(assignments__effective_from__lte=today),
            Q(assignments__effective_to__isnull=True)
            | Q(assignments__effective_to__gte=today),
        )

    for team in teams or []:
        queryset = queryset.filter(
            memberships__team__name__iexact=team, memberships__left_on__isnull=True
        )

    for specialisation in specialisations or []:
        queryset = queryset.filter(
            specialisations__name__iexact=specialisation,
            specialisations__hidden=False,
            specialisations__is_active=True,
        )

    roles = [r.lower() for r in roles or []]
    if roles:
        unknown = [r for r in roles if r not in ROLES]
        if unknown: raise MemberFilterError(
            f"Unknown role: {', '.join(unknown)}. Allowed: {', '.join(ROLES)}."
        )
        queryset = queryset.filter(
            memberships__role__in=roles, memberships__left_on__isnull=True
        )

    genders = [g.lower() for g in genders or []]
    if genders:
        unknown = [g for g in genders if g not in GENDERS]
        if unknown: raise MemberFilterError(
            f"Unknown gender: {', '.join(unknown)}. Allowed: {', '.join(GENDERS)}."
        )
        queryset = queryset.filter(gender__in=genders)

    if nationality:
        queryset = queryset.filter(nationality__icontains=nationality)

    if hometown:
        queryset = queryset.filter(hometown__icontains=hometown)

    if school:
        queryset = queryset.filter(
            education__school__icontains=school, education__hidden=False
        )

    if certificate:
        queryset = queryset.filter(
            Q(certificates__course_name__icontains=certificate, certificates__hidden=False)
            | Q(education__certificate_title__icontains=certificate, education__hidden=False)
        )

    if search: queryset = queryset.filter(
        Q(user__first_name__icontains=search)
        | Q(user__last_name__icontains=search)
        | Q(staff_id__icontains=search)
        | Q(about__icontains=search)
        | Q(specialisations__name__icontains=search)
        | Q(assignments__position__name__icontains=search)
    )

    if started_after:
        queryset = queryset.filter(started_on__gte=_parse_date(started_after, 'started_after'))

    if started_before:
        queryset = queryset.filter(started_on__lte=_parse_date(started_before, 'started_before'))

    if is_active is not None:
        queryset = queryset.filter(
            ended_on__isnull=_parse_bool(is_active, 'is_active')
        )

    if has_image is not None:
        queryset = (
            queryset.exclude(profile_image='')
            if _parse_bool(has_image, 'has_image')
            else queryset.filter(profile_image='')
        )

    if ordering:
        field = ordering.lstrip('-')
        if field not in ORDERING_FIELDS:
            raise MemberFilterError(
                f"Cannot order by '{ordering}'. "
                f"Allowed: {', '.join(sorted(ORDERING_FIELDS))}."
            )
        prefix = '-' if ordering.startswith('-') else ''
        queryset = queryset.order_by(*(f'{prefix}{f}' for f in ORDERING_FIELDS[field]))

    # Joins across assignments/teams/education duplicate rows, so counts would lie.
    return queryset.distinct()


def _parse_bool(value, name):
    if value.lower() in ('true', '1'): return True
    if value.lower() in ('false', '0'): return False
    raise MemberFilterError(f'{name} must be true or false.')


def _parse_date(value, name):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise MemberFilterError(f'{name} must be a date in YYYY-MM-DD form.')
