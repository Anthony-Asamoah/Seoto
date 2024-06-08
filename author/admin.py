from django.contrib import admin

from .models import Message, Stack


@admin.register(Stack)
class StackAdmin(admin.ModelAdmin):
	list_display = ['id', 'is_active', 'label']
	list_display_links = ['label']
	list_editable = ['is_active']
	ordering = ['id']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
	list_display = ['name', 'email', 'subject', 'message', 'replied']
	list_display_links = list_display[:-1]
	list_filter = ['replied', 'email']
	search_fields = ['email', 'subject', 'message', 'name']
	list_editable = ['replied']
	list_per_page = 20

