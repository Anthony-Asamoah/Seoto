from django.contrib import admin
from django.utils.html import format_html, mark_safe, strip_tags

from utils.admin import RichTextAdminMixin
from .models import meal, userPreference, MealTimeSlot, UserMealSchedule


@admin.register(MealTimeSlot)
class MealTimeSlotAdmin(admin.ModelAdmin):
    list_display = ['label', 'default_time']
    ordering = ['default_time']


@admin.register(UserMealSchedule)
class UserMealScheduleAdmin(admin.ModelAdmin):
    list_display = ['user', 'slot', 'time']
    list_filter = ['slot']
    search_fields = ['user__username']
    autocomplete_fields = ['user']
    ordering = ['slot', 'user']
    list_per_page = 20


@admin.register(meal)
class mealAdmin(RichTextAdminMixin, admin.ModelAdmin):
    richtext_fields = ('description', 'ingredients', 'nutrients', 'benefits')

    exclude = ['main_img_thumbnail']

    list_display = ['meal_icon', 'name', 'description_preview', 'default_preference', 'is_public', 'created_by', 'cooking_duration']
    list_display_links = ['name']
    search_fields = ['name', 'description', 'ingredients']
    list_filter = ['is_public', 'created_by', 'cooking_duration', 'default_preference']
    list_per_page = 20

    @admin.display(description='')
    def meal_icon(self, obj):
        if obj.main_img_thumbnail:
            return format_html(
                '<img src="{}" style="width:36px;height:36px;border-radius:50%;object-fit:cover;">',
                obj.main_img_thumbnail.url
            )
        return mark_safe(
            '<span style="display:inline-flex;align-items:center;justify-content:center;'
            'width:36px;height:36px;border-radius:50%;background:#e9e9e9;font-size:18px;">🍽️</span>'
        )

    @admin.display(description='Description')
    def description_preview(self, obj):
        text = strip_tags(obj.description)
        return (text[:60] + '…') if len(text) > 60 else text


@admin.register(userPreference)
class userPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'meal', 'slot', 'isAvailable']
    list_filter = ['slot', 'isAvailable']
    search_fields = ['user__username', 'meal__name']
    autocomplete_fields = ['user', 'meal']
    list_per_page = 20

