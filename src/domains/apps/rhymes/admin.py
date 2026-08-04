from django.contrib import admin

from .models import Rhyme


@admin.register(Rhyme)
class RhymeAdmin(admin.ModelAdmin):
    list_display = ('rhyme', 'word_count', 'timestamp', 'user')
    list_display_links = ('rhyme',)
    list_filter = ('user',)
    search_fields = ('rhyme', 'text')
    list_per_page = 20
    date_hierarchy = 'timestamp'

    fieldsets = (
        (None, {
            'fields': ('rhyme', 'text', 'word_count')
        }),
        ('User', {
            'fields': ('user',)
        }),
        ('Timestamp', {
            'fields': ('timestamp',)
        }),
    )
