from django.contrib import admin

from .models import message, stack


@admin.register(stack)
class stackAdmin(admin.ModelAdmin):
	list_display = ['id', 'is_active', 'label']
	list_display_links = ['label']
	list_editable = ['is_active']
	ordering = ['id']


@admin.register(message)
class messageAdmin(admin.ModelAdmin):
	list_display = ['name', 'email', 'subject', 'message', 'replied']
	list_display_links = list_display[:-1]
	list_filter = ['replied', 'email']
	search_fields = ['email', 'subject', 'message', 'name']
	list_editable = ['replied']
	list_per_page = 20

