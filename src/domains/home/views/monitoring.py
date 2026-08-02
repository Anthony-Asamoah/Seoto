from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from domains.author.models import Message
from domains.home.models import ErrorLog

User = get_user_model()


def _is_staff(user):
    return user.is_staff


# ── Errors ────────────────────────────────────────────────────────────────────

@login_required
@user_passes_test(_is_staff)
def errors_list(request):
    level = request.GET.get('level', '')
    logs = ErrorLog.objects.all()
    if level:
        logs = logs.filter(level=level)
    context = {
        'logs': logs[:200],
        'level': level,
        'levels': ['WARNING', 'ERROR', 'CRITICAL'],
    }
    return render(request, 'Home/dashboard/errors.html', context)


# ── User analytics ─────────────────────────────────────────────────────────────

@login_required
@user_passes_test(_is_staff)
def user_analytics(request):
    now = timezone.now()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    # Registrations per day (last 30 days) — list of (date_str, count)
    from django.db.models.functions import TruncDate
    from django.db.models import Count

    daily_regs = (
        User.objects
        .filter(date_joined__gte=month_ago)
        .annotate(day=TruncDate('date_joined'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )

    context = {
        'total_users': User.objects.count(),
        'active_users': User.objects.filter(is_active=True).count(),
        'staff_users': User.objects.filter(is_staff=True).count(),
        'new_week': User.objects.filter(date_joined__gte=week_ago).count(),
        'new_month': User.objects.filter(date_joined__gte=month_ago).count(),
        'recently_active': User.objects.filter(last_login__gte=week_ago).count(),
        'daily_regs': list(daily_regs),
    }
    return render(request, 'Home/dashboard/users.html', context)


# ── App usage analytics ────────────────────────────────────────────────────────

@login_required
@user_passes_test(_is_staff)
def app_usage(request):
    from domains.apps.blog.models import Post
    from domains.apps.jotter.models import todo, tracker
    from domains.apps.spending_tracker.models import Transaction

    month_ago = timezone.now() - timedelta(days=30)
    week_ago = timezone.now() - timedelta(days=7)

    apps = [
        {
            'name': 'Spending Tracker',
            'total': Transaction.objects.count(),
            'week': Transaction.objects.filter(created_at__gte=week_ago).count(),
            'month': Transaction.objects.filter(created_at__gte=month_ago).count(),
        },
        {
            'name': 'Blog',
            'total': Post.objects.count(),
            'week': Post.objects.filter(date_posted__gte=week_ago).count(),
            'month': Post.objects.filter(date_posted__gte=month_ago).count(),
        },
        {
            'name': 'Jotter (Todos)',
            'total': todo.objects.count(),
            'week': todo.objects.filter(added_on__gte=week_ago).count(),
            'month': todo.objects.filter(added_on__gte=month_ago).count(),
        },
        {
            'name': 'Jotter (Tracker)',
            'total': tracker.objects.count(),
            'week': tracker.objects.filter(added_on__gte=week_ago).count(),
            'month': tracker.objects.filter(added_on__gte=month_ago).count(),
        },
        {
            'name': 'Messages (Contact)',
            'total': Message.objects.count(),
            'week': Message.objects.filter(submitted_on__gte=week_ago).count(),
            'month': Message.objects.filter(submitted_on__gte=month_ago).count(),
        },
    ]

    context = {'apps': apps}
    return render(request, 'Home/dashboard/usage.html', context)


# ── Messages ──────────────────────────────────────────────────────────────────

@login_required
@user_passes_test(_is_staff)
def messages_list(request):
    qs = Message.objects.all().order_by('-submitted_on')

    replied = request.GET.get('replied', '')
    search = request.GET.get('q', '').strip()

    if replied == 'yes':
        qs = qs.filter(replied=True)
    elif replied == 'no':
        qs = qs.filter(replied=False)

    if search:
        qs = qs.filter(name__icontains=search) | qs.filter(subject__icontains=search) | qs.filter(message__icontains=search)

    context = {
        'contact_messages': qs[:100],
        'replied': replied,
        'search': search,
        'total': Message.objects.count(),
        'unread': Message.objects.filter(replied=False).count(),
    }
    return render(request, 'Home/dashboard/messages.html', context)


@login_required
@user_passes_test(_is_staff)
def message_detail(request, pk):
    msg = get_object_or_404(Message, pk=pk)

    if request.method == 'POST':
        msg.replied = not msg.replied
        msg.save(update_fields=['replied'])
        return redirect('message_detail', pk=pk)

    return render(request, 'Home/dashboard/message_detail.html', {'msg': msg})
