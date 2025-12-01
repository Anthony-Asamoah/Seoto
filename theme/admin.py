from django.contrib import admin
from .models import ThemePreset, UserTheme, ThemeRating


class ThemeRatingInline(admin.TabularInline):
    """Inline display of ratings for a theme"""
    model = ThemeRating
    extra = 0
    readonly_fields = ('user', 'rating', 'created_at')
    can_delete = True


@admin.register(ThemePreset)
class ThemePresetAdmin(admin.ModelAdmin):
    """Admin interface for ThemePreset model"""
    list_display = (
        'name',
        'created_by',
        'is_official',
        'is_featured',
        'is_public',
        'is_public_verified',
        'average_rating',
        'rating_count',
        'created_at'
    )
    list_filter = (
        'is_official',
        'is_featured',
        'is_public',
        'is_public_verified',
        'created_at'
    )
    search_fields = ('name', 'description', 'created_by__username')
    readonly_fields = ('created_at', 'updated_at', 'rating_count', 'rating_sum', 'average_rating')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'created_by')
        }),
        ('Base Colors', {
            'fields': (
                'primary_color',
                'secondary_color',
                'background_color',
                'text_color',
                'text_head_color',
            )
        }),
        ('Navbar Colors', {
            'fields': (
                'navbar_bg',
                'navbar_text'
            )
        }),
        ('Button Colors', {
            'fields': (
                ('btn_success_bg', 'btn_success_text'),
                ('btn_danger_bg', 'btn_danger_text'),
                ('btn_warning_bg', 'btn_warning_text'),
                ('btn_info_bg', 'btn_info_text'),
            ),
            'classes': ('collapse',)
        }),
        ('Card Colors', {
            'fields': (
                'card_bg_color',
                'card_header_bg_color',
                'card_text_color',
            ),
            'classes': ('collapse',)
        }),
        ('Status & Visibility', {
            'fields': (
                'is_official',
                'is_public',
                'is_public_verified',
                'is_featured'
            )
        }),
        ('Rating Statistics', {
            'fields': ('rating_count', 'rating_sum', 'average_rating'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    inlines = [ThemeRatingInline]

    def average_rating(self, obj):
        """Display average rating in admin"""
        return obj.average_rating
    average_rating.short_description = 'Avg Rating'

    actions = ['make_official', 'make_featured', 'verify_public', 'unverify_public']

    def make_official(self, request, queryset):
        """Bulk action to make themes official"""
        updated = queryset.update(is_official=True)
        self.message_user(request, f'{updated} theme(s) marked as official.')
    make_official.short_description = 'Mark selected themes as official'

    def make_featured(self, request, queryset):
        """Bulk action to make themes featured"""
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} theme(s) marked as featured.')
    make_featured.short_description = 'Mark selected themes as featured'

    def verify_public(self, request, queryset):
        """Bulk action to verify public themes"""
        updated = queryset.filter(is_public=True).update(is_public_verified=True)
        self.message_user(request, f'{updated} public theme(s) verified.')
    verify_public.short_description = 'Verify selected public themes'

    def unverify_public(self, request, queryset):
        """Bulk action to unverify public themes"""
        updated = queryset.update(is_public_verified=False)
        self.message_user(request, f'{updated} theme(s) unverified.')
    unverify_public.short_description = 'Unverify selected themes'


@admin.register(UserTheme)
class UserThemeAdmin(admin.ModelAdmin):
    """Admin interface for UserTheme model"""
    list_display = (
        'user',
        'is_using_preset',
        'active_preset',
        'updated_at'
    )
    list_filter = ('is_using_preset', 'updated_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('updated_at',)
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Theme Configuration', {
            'fields': ('is_using_preset', 'active_preset')
        }),
        ('Custom Base Colors', {
            'fields': (
                'custom_primary_color',
                'custom_secondary_color',
                'custom_background_color',
                'custom_text_color',
                'custom_text_head_color',
                'custom_navbar_bg',
                'custom_navbar_text'
            ),
            'classes': ('collapse',)
        }),
        ('Custom Button Colors', {
            'fields': (
                ('custom_btn_success_bg', 'custom_btn_success_text'),
                ('custom_btn_danger_bg', 'custom_btn_danger_text'),
                ('custom_btn_warning_bg', 'custom_btn_warning_text'),
                ('custom_btn_info_bg', 'custom_btn_info_text'),
            ),
            'classes': ('collapse',)
        }),
        ('Custom Card Colors', {
            'fields': (
                'custom_card_bg_color',
                'custom_card_header_bg_color',
                'custom_card_text_color',
            ),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('updated_at',),
            'classes': ('collapse',)
        })
    )


@admin.register(ThemeRating)
class ThemeRatingAdmin(admin.ModelAdmin):
    """Admin interface for ThemeRating model"""
    list_display = ('user', 'theme', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('user__username', 'theme__name')
    readonly_fields = ('created_at',)
    fieldsets = (
        ('Rating Information', {
            'fields': ('user', 'theme', 'rating')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )
