from django.contrib import admin
from django.utils.html import format_html, mark_safe, strip_tags
from django_ckeditor_5.widgets import CKEditor5Widget

from .models import meal, userPreference, MealOrder

_RICHTEXT_FIELDS = ('description', 'ingredients', 'nutrients', 'benefits')


@admin.register(meal)
class mealAdmin(admin.ModelAdmin):
    list_display = ['meal_icon', 'name', 'description_preview', 'is_public', 'created_by', 'cooking_duration']
    list_display_links = ['name']
    search_fields = ['name', 'description', 'ingredients']
    list_filter = ['is_public', 'created_by', 'cooking_duration']
    list_per_page = 20

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        for field_name in _RICHTEXT_FIELDS:
            if field_name in form.base_fields:
                form.base_fields[field_name].widget = CKEditor5Widget(config_name='default')
        return form

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
