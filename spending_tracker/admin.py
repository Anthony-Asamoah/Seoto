from django.contrib import admin

from .models import Tag, Category, Account, Transaction


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['label', 'created_at', 'user']
    search_fields = ['label', 'user__username']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['label', 'description', 'created_at', 'user']
    search_fields = ['label', 'description', 'user__username']


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'balance', 'created_at']
    search_fields = ['name', 'user__username']
    readonly_fields = ['created_at', 'balance']


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['mode', 'amount', 'currency', 'account', 'category', 'created_at']
    list_filter = ['mode', 'currency', 'category', 'created_at']
    search_fields = ['details', 'reference', 'account__name']
    filter_horizontal = ['tags']
    readonly_fields = ['created_at', ]
    date_hierarchy = 'created_at'
