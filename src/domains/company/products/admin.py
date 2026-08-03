from django.contrib import admin

from infrastructure.core.utils import RichTextAdminMixin
from .models import Product, ProductImage, ProductTag


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image', 'alt_text', 'caption', 'is_cover', 'order')


class ProductAdmin(RichTextAdminMixin, admin.ModelAdmin):
    richtext_fields = ('body',)

    list_display = ('title', 'client', 'status', 'is_featured', 'launched_on', 'order')
    list_filter = ('status', 'is_featured', 'tags')
    list_editable = ('status', 'is_featured', 'order')
    search_fields = ('title', 'client', 'summary', 'body')
    autocomplete_fields = ('tags',)
    prepopulated_fields = {'slug': ('title',)}
    inlines = (ProductImageInline,)

    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'client')
        }),
        ('Copy', {
            'fields': ('summary', 'body', 'outcome'),
            'description': 'Summary is the collapsed line; body shows when the listing expands.',
        }),
        ('Credits', {
            'fields': ('contributors', 'sponsors'),
            'description': 'JSON lists of names, e.g. ["Ada Lovelace", "Alan Turing"].',
        }),
        ('Publication', {
            'fields': ('status', 'is_featured', 'launched_on', 'live_url', 'order'),
            'description': 'Drafts are never served by the API. Featured products sort first.',
        }),
        ('Categorization', {
            'fields': ('tags',)
        }),
    )


class ProductTagAdmin(admin.ModelAdmin):
    list_display = ('label', 'order')
    list_editable = ('order',)
    search_fields = ('label',)


admin.site.register(Product, ProductAdmin)
admin.site.register(ProductTag, ProductTagAdmin)
