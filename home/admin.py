from django.contrib import admin

from home.models import ErrorLog


@admin.register(ErrorLog)
class ErrorLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'level', 'logger_name', 'message_preview')
    list_filter = ('level',)
    readonly_fields = ('level', 'logger_name', 'message', 'traceback', 'path', 'method', 'user_id', 'timestamp')
    ordering = ('-timestamp',)
    date_hierarchy = 'timestamp'

    def message_preview(self, obj):
        return obj.message[:100]
    message_preview.short_description = 'Message'

    def has_add_permission(self, request):
        return False
