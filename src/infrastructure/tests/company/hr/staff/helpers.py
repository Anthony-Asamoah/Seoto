from datetime import date

from django.contrib.auth import get_user_model

from domains.company.hr.staff.models import Assignment, Member


User = get_user_model()


def make_member(username, **kwargs):
    user = User.objects.create_user(username=username)
    return Member.objects.create(user=user, started_on=date(2026, 1, 1), **kwargs)


def make_assignment(member, position, effective_from, effective_to=None, salary=1000):
    return Assignment.objects.create(
        member=member, position=position, salary=salary,
        effective_from=effective_from, effective_to=effective_to,
    )
