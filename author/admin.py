from django.contrib import admin
from .models import contact


@admin.register(contact)
class contactAdmin(admin.ModelAdmin):
	list_display = ['name', 'email', 'subject', 'message', 'replied']
	list_display_links = list_display[:-1]
	list_filter = ['replied', 'email']
	search_fields = ['email', 'subject', 'message', 'name']
	list_editable = ['replied']
	list_per_page = 20
	ordering = []

