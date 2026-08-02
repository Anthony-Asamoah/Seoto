from django.contrib import admin

from .models import Tag, Category, Account, Transaction, RecurringTransaction, RecurringTransactionOccurrence


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


@admin.register(RecurringTransaction)
class RecurringTransactionAdmin(admin.ModelAdmin):
    list_display = ['mode', 'amount', 'account', 'frequency', 'next_run_date', 'is_auto_renew', 'is_active', 'user']
    list_filter = ['mode', 'frequency', 'is_auto_renew', 'is_active']
    search_fields = ['details', 'reference', 'account__name', 'user__username']
    filter_horizontal = ['tags']
    readonly_fields = ['created_at', 'updated_at', 'last_run_at']
    date_hierarchy = 'next_run_date'


@admin.register(RecurringTransactionOccurrence)
class RecurringTransactionOccurrenceAdmin(admin.ModelAdmin):
    list_display = ['recurring_transaction', 'scheduled_date', 'status', 'transaction', 'resolved_at']
    list_filter = ['status']
    search_fields = ['recurring_transaction__details', 'recurring_transaction__user__username']
    readonly_fields = ['created_at']
    date_hierarchy = 'scheduled_date'
