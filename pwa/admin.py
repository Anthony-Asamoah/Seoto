import logging

from django.contrib import admin
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import path, reverse

from .models import PushSubscription, Notification
from .views import send_push_notification

logger = logging.getLogger(__name__)


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'endpoint_preview', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['user__username', 'endpoint']
    readonly_fields = ['created_at', 'updated_at']
    actions = ['send_push_notification_action']

    def endpoint_preview(self, obj):
        return obj.endpoint[:50] + '...'

    endpoint_preview.short_description = 'Endpoint'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [path(
            'send-push/',
            self.admin_site.admin_view(self.send_push_view),
            name='pwa_pushsubscription_send_push',
        ), ]
        return custom_urls + urls

    @admin.action(description='Send push notification to selected subscriptions')
    def send_push_notification_action(self, request, queryset):
        selected_ids = list(queryset.values_list('id', flat=True))
        request.session['push_selected_ids'] = selected_ids
        return HttpResponseRedirect(reverse('admin:pwa_pushsubscription_send_push'))

    def send_push_view(self, request):
        selected_ids = request.session.get('push_selected_ids', [])
        subscriptions = PushSubscription.objects.filter(id__in=selected_ids).select_related('user')

        if request.method == 'POST':
            title = request.POST.get('title', '').strip()
            body = request.POST.get('body', '').strip()
            url = request.POST.get('url', '').strip() or '/'

            if not title or not body:
                self.message_user(request, 'Title and body are required.', level='error')
            else:
                seen_users = set()
                success_count = 0
                for sub in subscriptions:
                    if sub.user_id not in seen_users:
                        seen_users.add(sub.user_id)
                        success_count += send_push_notification(sub.user, title, body, url=url)

                del request.session['push_selected_ids']
                self.message_user(
                    request,
                    f'Push notification sent to {len(seen_users)} user(s), '
                    f'{success_count} device(s) reached.'
                )
                return HttpResponseRedirect(
                    reverse('admin:pwa_pushsubscription_changelist')
                )

        context = {
            **self.admin_site.each_context(request),
            'title': 'Send Push Notification',
            'subscriptions': subscriptions,
            'opts': self.model._meta,
        }
        return render(request, 'admin/pwa/send_push_notification.html', context)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'sent', 'sent_at', 'created_at']
    list_filter = ['sent', 'created_at']
    search_fields = ['user__username', 'title', 'body']
    readonly_fields = ['created_at', 'sent_at']
