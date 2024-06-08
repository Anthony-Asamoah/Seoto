from django.contrib import admin
from .models import tracker, todo


@admin.register(tracker)
class trackerAdmin(admin.ModelAdmin):
	list_display = ['isCompleted', 'user', 'category', 'title', 'chapter', 'episode', 'timestamp', 'link']
	list_display_links = list_display
	list_filter = ['isCompleted', 'category', 'user']
	search_fields = list_display[:2]
	list_per_page = 20


@admin.register(todo)
class todoAdmin(admin.ModelAdmin):
	list_display = ['isCompleted', 'user', 'title', 'priority', 'reminder']
	list_filter = ['isCompleted', 'user', 'priority']
	list_per_page = 20
	search_fields = ['user', 'title']
	list_display_links = list_display[1:]
