from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from django.utils import timezone

User = get_user_model()


def _is_staff(user):
    return user.is_staff


@login_required
@user_passes_test(_is_staff)
def dashboard(request):
    from domains.apps.blog.models import Post
    from domains.home.models import ErrorLog
    from domains.apps.spending_tracker.models import Transaction

    week_ago = timezone.now() - timedelta(days=7)

    context = {
        'total_users': User.objects.count(),
        'new_users_week': User.objects.filter(date_joined__gte=week_ago).count(),
        'error_count_week': ErrorLog.objects.filter(timestamp__gte=week_ago).count(),
        'transactions_week': Transaction.objects.filter(created_at__gte=week_ago).count(),
        'posts_week': Post.objects.filter(date_posted__gte=week_ago).count(),
        'year': datetime.now().year,
    }
    return render(request, 'Home/dashboard/overview.html', context)
