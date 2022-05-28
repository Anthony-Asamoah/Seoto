from django.contrib import admin
from .models import meal


@admin.register(meal)
class mealAdmin(admin.ModelAdmin):
	list_display = [
		'name', 'description',
		'IsAvailable', 'isBreakfast', 'isBrunch', 'isLunch', 'isDinner', 'isExtra', 'isFancy'
	]
	list_editable = list_display[2:]
	list_display_links = list_display[:1]
	list_filter = ['cooking_duration'] + list_display[2:]
	search_fields = list_display[:2]
	list_per_page = 10
