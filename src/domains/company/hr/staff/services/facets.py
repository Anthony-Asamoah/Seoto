from django.utils import timezone

from ..models import Position, Specialisation, Team


def list_public_position_names():
    """Every position currently held by a public member."""
    today = timezone.localdate()
    return list(
        Position.objects
        .filter(
            assignments__member__is_public=True,
            assignments__effective_from__lte=today,
        )
        .exclude(assignments__effective_to__lt=today)
        .values_list('name', flat=True)
        .order_by('name')
        .distinct()
    )


def list_public_team_names():
    """Every active team carrying at least one public member."""
    return list(
        Team.objects
        .filter(is_active=True, memberships__left_on__isnull=True,
                memberships__member__is_public=True)
        .values_list('name', flat=True)
        .order_by('name')
        .distinct()
    )


def list_public_specialisation_names():
    """Every visible specialisation claimed by a public member."""
    return list(
        Specialisation.objects
        .filter(hidden=False, is_active=True, member__is_public=True)
        .values_list('name', flat=True)
        .order_by('name')
        .distinct()
    )
