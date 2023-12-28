from django.contrib import admin

from rhymes.models import Rhyme


@admin.register(Rhyme)
class RhymeAdmin(admin.ModelAdmin):
    list_display = (
        "rhyme",
        "word_count",
        "timestamp",
    )
    list_display_links = list_display
    list_filter = ("rhyme", "user")
    search_fields = ('rhyme',)
    list_per_page = 20
