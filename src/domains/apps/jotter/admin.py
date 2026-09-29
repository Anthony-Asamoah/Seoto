from django.contrib import admin
from common.mixins.admin import OwnerScopedAdminMixin

from .models import tracker, todo


@admin.register(tracker)
class TrackerAdmin(OwnerScopedAdminMixin, admin.ModelAdmin):
    list_display = ['user', 'category', 'title', 'episode', 'chapter', 'timestamp', 'link', 'isCompleted', 'added_on']
    list_display_links = ['title']
    list_filter = ['category', 'isCompleted']
    search_fields = ['user__username', 'title']
    list_per_page = 20
    date_hierarchy = 'added_on'

    fieldsets = (
        (None, {
            'fields': ('title', 'category')
        }),
        ('Details', {
            'fields': ('episode', 'chapter', 'timestamp', 'link')
        }),
        ('User', {
            'fields': ('user',)
        }),
        ('Status', {
            'fields': ('isCompleted', 'added_on')
        }),
    )


@admin.register(todo)
class TodoAdmin(OwnerScopedAdminMixin, admin.ModelAdmin):
    list_display = ['user', 'title', 'priority', 'reminder', 'isCompleted', 'added_on']
    list_display_links = ['title']
    list_filter = ['priority', 'isCompleted']
    search_fields = ['user__username', 'title']
    list_per_page = 20
    date_hierarchy = 'added_on'

    fieldsets = (
        (None, {
            'fields': ('title', 'priority')
        }),
        ('Details', {
            'fields': ('notes', 'reminder')
        }),
        ('User', {
            'fields': ('user',)
        }),
        ('Status', {
            'fields': ('isCompleted', 'added_on')
        }),
    )
