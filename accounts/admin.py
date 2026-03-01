from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html, mark_safe

from .models import user_profile


@admin.register(user_profile)
class user_profileAdmin(admin.ModelAdmin):
    list_display = ['profile_icon', 'user', 'contact']
    list_display_links = ['user']
    list_per_page = 20

    @admin.display(description='')
    def profile_icon(self, obj):
        if obj.picture_thumbnail:
            return format_html(
                '<img src="{}" style="width:36px;height:36px;border-radius:50%;object-fit:cover;">',
                obj.picture_thumbnail.url
            )
        return mark_safe(
            '<span style="display:inline-flex;align-items:center;justify-content:center;'
            'width:36px;height:36px;border-radius:50%;background:#e9e9e9;font-size:18px;">👤</span>'
        )


admin.site.unregister(User)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['user_icon', 'username', 'email', 'first_name', 'last_name', 'is_staff']

    @admin.display(description='')
    def user_icon(self, obj):
        try:
            thumb = obj.user_profile.picture_thumbnail
            if thumb:
                return format_html(
                    '<img src="{}" style="width:36px;height:36px;border-radius:50%;object-fit:cover;">',
                    thumb.url
                )
        except user_profile.DoesNotExist:
            pass
        return mark_safe(
            '<span style="display:inline-flex;align-items:center;justify-content:center;'
            'width:36px;height:36px;border-radius:50%;background:#e9e9e9;font-size:18px;">👤</span>'
        )
