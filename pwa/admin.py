from django.contrib import admin
from .models import PushSubscription, Notification


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'endpoint_preview', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['user__username', 'endpoint']
    readonly_fields = ['created_at', 'updated_at']

    def endpoint_preview(self, obj):
        return obj.endpoint[:50] + '...'
    endpoint_preview.short_description = 'Endpoint'


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'sent', 'sent_at', 'created_at']
    list_filter = ['sent', 'created_at']
    search_fields = ['user__username', 'title', 'body']
    readonly_fields = ['created_at', 'sent_at']
