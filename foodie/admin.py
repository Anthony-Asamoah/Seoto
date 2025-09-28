from django.contrib import admin

from .models import meal, userPreference


@admin.register(meal)
class mealAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'description',
    ]
    list_editable = list_display[2:]
    list_display_links = list_display[:1]
    list_filter = ['cooking_duration'] + list_display[2:]
    search_fields = list_display[:2]
    list_per_page = 10


@admin.register(userPreference)
class userPreferenceAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'meal', 'isAvailable', 'isBreakfast', 'isBrunch', 'isLunch', 'isDinner', 'isExtra', 'isFancy'
    ]
    list_filter = ['user', 'meal', 'isAvailable', 'isBreakfast', 'isBrunch', 'isLunch', 'isDinner', 'isExtra', 'isFancy']
    search_fields = ['user__username', 'meal__name']
    autocomplete_fields = ['user', 'meal']
    list_per_page = 10
