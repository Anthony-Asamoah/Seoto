from django.contrib import admin

from .models import meal, userPreference, MealOrder


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
    list_filter = [
        'user', 'meal', 'isAvailable', 'isBreakfast', 'isBrunch', 'isLunch', 'isDinner', 'isExtra',
        'isFancy'
    ]
    search_fields = ['user__username', 'meal__name']
    autocomplete_fields = ['user', 'meal']
    list_per_page = 10


@admin.register(MealOrder)
class MealOrderAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'meal',
        'quantity',
        'location',
        'price',
        'details',
        'is_confirmed',
        'is_purchased',
        'is_delivered',
        'not_available',
    ]
    list_editable = [
        'is_confirmed',
        'is_purchased',
        'is_delivered',
        'not_available',
    ]
    list_display_links = [
        'user',
        'meal',
        'quantity',
        'location',
        'price',
        'details',
    ]
    list_filter = [
        'date_ordered',
        'is_confirmed',
        'is_purchased',
        'is_delivered',
        'not_available',
        'location',
        'user',
        'meal',
    ]
    search_fields = [
        'user__username',
        'user__first_name',
        'user__last_name',
        'user__email',
        'meal__name',
        'details',
    ]
    autocomplete_fields = ['user', 'meal']
    date_hierarchy = 'date_ordered'
    ordering = ['-date_ordered']
    list_per_page = 20
