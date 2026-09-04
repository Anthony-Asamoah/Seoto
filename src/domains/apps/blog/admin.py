from django.contrib import admin

from infrastructure.utils import RichTextAdminMixin
from .models import Post, PostTags, PostReadGroup, PostComment


class PostAdmin(RichTextAdminMixin, admin.ModelAdmin):
    richtext_fields = ('content',)
    richtext_config = 'blog'

    list_display = ('title', 'author', 'date_posted', 'is_public')
    list_display_links = ('title',)
    list_filter = ('is_public', 'date_posted', 'author', 'tags')
    search_fields = ('title', 'content')
    autocomplete_fields = ('tags', 'allowed_groups', 'allowed_users')
    date_hierarchy = 'date_posted'

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
    list_display = ('hits', 'label')
    search_fields = ('label',)
    ordering = ('-hits',)


class PostReadGroupAdmin(admin.ModelAdmin):
    list_display = ('label',)
    search_fields = ('label',)


class PostCommentAdmin(admin.ModelAdmin):
    list_display = ('post', 'author', 'date_posted', 'is_visible', 'edited')
    list_display_links = ('post',)
    list_filter = ('is_visible', 'date_posted', 'edited')
    search_fields = ('content', 'author__username', 'post__title')
    list_editable = ('is_visible',)
    date_hierarchy = 'date_posted'


admin.site.register(Post, PostAdmin)
admin.site.register(PostTags, PostTagsAdmin)
admin.site.register(PostReadGroup, PostReadGroupAdmin)
admin.site.register(PostComment, PostCommentAdmin)
