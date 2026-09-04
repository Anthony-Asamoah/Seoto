from django.contrib import admin
from django.utils.html import format_html

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
    list_display = ['name', 'user', 'account_type', 'balance', 'is_default', 'created_at']
    list_display_links = ['name']
    list_filter = ['account_type', 'is_default']
    search_fields = ['name', 'user__username']
    readonly_fields = ['created_at', 'balance']
    date_hierarchy = 'created_at'

    fieldsets = (
        (None, {
            'fields': ('name', 'account_type', 'balance', 'is_default')
        }),
        ('User', {
            'fields': ('user',)
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        }),
    )


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['mode', 'amount', 'currency', 'account', 'category', 'transaction_time', 'created_at']
    list_display_links = ['mode', 'amount']
    list_filter = ['mode', 'currency', 'category', 'created_at']
    search_fields = ['details', 'reference', 'account__name', 'category__label']
    readonly_fields = ['created_at', 'transaction_time']
    date_hierarchy = 'transaction_time'

    fieldsets = (
        (None, {
            'fields': ('mode', 'amount', 'currency', 'account', 'category')
        }),
        ('Details', {
            'fields': ('details', 'reference', 'attachment')
        }),
        ('Tags', {
            'fields': ('tags',)
        }),
        ('Timestamps', {
            'fields': ('transaction_time', 'created_at')
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('account', 'category').prefetch_related('tags')


@admin.register(RecurringTransaction)
class RecurringTransactionAdmin(admin.ModelAdmin):
    list_display = ['mode', 'amount', 'currency', 'account', 'frequency', 'next_run_date', 'is_auto_renew', 'is_active', 'user']
    list_display_links = ['mode', 'amount']
    list_filter = ['mode', 'frequency', 'is_auto_renew', 'is_active']
    search_fields = ['details', 'reference', 'account__name', 'user__username']
    readonly_fields = ['created_at', 'updated_at', 'last_run_at']
    date_hierarchy = 'next_run_date'

    fieldsets = (
        (None, {
            'fields': ('mode', 'amount', 'currency', 'account', 'category')
        }),
        ('Details', {
            'fields': ('details', 'reference', 'notification_note')
        }),
        ('Scheduling', {
            'fields': ('frequency', 'custom_type', 'custom_weekdays', 'custom_month_days', 'renewal_date', 'next_run_date', 'end_date')
        }),
        ('Behaviour', {
            'fields': ('is_auto_renew', 'is_active')
        }),
        ('User', {
            'fields': ('user',)
        }),
        ('Timestamps', {
            'fields': ('last_run_at', 'created_at', 'updated_at')
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('account', 'category').prefetch_related('tags')


@admin.register(RecurringTransactionOccurrence)
class RecurringTransactionOccurrenceAdmin(admin.ModelAdmin):
    list_display = ['recurring_transaction', 'scheduled_date', 'status', 'transaction', 'resolved_at']
    list_display_links = ['recurring_transaction']
    list_filter = ['status']
    search_fields = ['recurring_transaction__details', 'recurring_transaction__user__username']
    readonly_fields = ['created_at']
    date_hierarchy = 'scheduled_date'

    fieldsets = (
        (None, {
            'fields': ('recurring_transaction', 'scheduled_date', 'status')
        }),
        ('Transaction', {
            'fields': ('transaction',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'resolved_at')
        }),
    )
