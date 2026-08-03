from django.contrib import admin

from infrastructure.utils import RichTextAdminMixin
from .models import FAQ, FAQCategory


class FAQInline(admin.TabularInline):
    model = FAQ
    extra = 1
    fields = ('question', 'is_published', 'is_featured', 'order')
    show_change_link = True


class FAQAdmin(RichTextAdminMixin, admin.ModelAdmin):
    richtext_fields = ('answer',)

    list_display = ('question', 'category', 'is_published', 'is_featured', 'order', 'updated_at')
    list_filter = ('is_published', 'is_featured', 'include_in_schema', 'category')
    list_editable = ('is_published', 'is_featured', 'order')
    search_fields = ('question', 'answer')
    autocomplete_fields = ('category',)
    prepopulated_fields = {'slug': ('question',)}

    fieldsets = (
        (None, {
            'fields': ('question', 'slug', 'category')
        }),
        ('Copy', {
            'fields': ('answer',)
        }),
        ('Publication', {
            'fields': ('is_published', 'is_featured', 'include_in_schema', 'order'),
            'description': 'Unpublished questions are never served by the API. '
                           'Featured questions sort first within their section.',
        }),
    )


class FAQCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'order')
    list_editable = ('order',)
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    inlines = (FAQInline,)


admin.site.register(FAQ, FAQAdmin)
admin.site.register(FAQCategory, FAQCategoryAdmin)
