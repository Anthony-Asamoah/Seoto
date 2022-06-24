from django.contrib import admin
from .models import user_profile


@admin.register(user_profile)
class user_profileAdmin(admin.ModelAdmin):
	list_display = ['user']
	list_display_links = list_display
	list_per_page = 20