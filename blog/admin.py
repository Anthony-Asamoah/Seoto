from django.contrib import admin

from .models import Post, PostTags, PostReadGroup


class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'date_posted', 'is_public')
    list_filter = ('is_public', 'date_posted', 'author', 'tags')
    search_fields = ('title', 'content')
    filter_horizontal = ('tags', 'allowed_groups', 'allowed_users')

    fieldsets = (
        (None, {
            'fields': ('title', 'content')
        }),
        ('Publication', {
            'fields': ('author', 'date_posted', 'is_public')
        }),
        ('Access Control', {
            'fields': ('allowed_groups', 'allowed_users')
        }),
        ('Categorization', {
            'fields': ('tags',)
        }),
    )


class PostTagsAdmin(admin.ModelAdmin):
    list_display = ('label',)
    search_fields = ('label',)


class PostReadGroupAdmin(admin.ModelAdmin):
    list_display = ('label',)
    filter_horizontal = ('users',)
    search_fields = ('label',)


admin.site.register(Post, PostAdmin)
admin.site.register(PostTags, PostTagsAdmin)
admin.site.register(PostReadGroup, PostReadGroupAdmin)
