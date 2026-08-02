import calendar
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from infrastructure.core.utils import BaseChoices


class TransactionModeChoices(BaseChoices):
    INCOME = 'INCOME', 'Income'
    EXPENSE = 'EXPENSE', 'Expense'
    TRANSFER = 'TRANSFER', 'Transfer'


class TransactionCurrencyChoices(BaseChoices):
    GHS = 'GHS', 'GHS'
    USD = 'USD', 'USD'
    EUR = 'EUR', 'EUR'
    GBP = 'GBP', 'GBP'


CURRENCY_SYMBOLS = {'GHS': '₵', 'USD': '$', 'EUR': '€', 'GBP': '£'}


class UserPreferences(models.Model):
    """User preferences for spending tracker"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='spending_preferences')
    default_currency = models.CharField(max_length=3, default='GHS', choices=[
        ('GHS', 'GHS'),
        ('USD', 'USD'),
        ('EUR', 'EUR'),
        ('GBP', 'GBP'),
    ])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s preferences"

    class Meta:
        verbose_name_plural = "User Preferences"


class Tag(models.Model):
    """Tags for categorizing transactions"""
    label = models.CharField(max_length=50, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tags')

    def __str__(self):
        return self.label.title()

    def save(self, *args, **kwargs):
        """Ensure label is saved in lowercase"""
        self.label = self.label.lower().strip()
        super().save(*args, **kwargs)

    @classmethod
    def get_or_create_from_input(cls, user, raw):
        """Resolve a comma-separated tag string to Tag rows, creating any that are new.

        `label` is unique app-wide, not per-user, so an existing tag is reused whoever
        first created it; `user` only decides who owns a brand-new one.
        """
        tags = []
        for label in [part.strip().lower() for part in (raw or '').split(',') if part.strip()]:
            tag, _ = cls.objects.get_or_create(label=label, defaults={'user': user})
            tags.append(tag)
        return tags

    class Meta:
        ordering = ['label']
        indexes = [
            models.Index(fields=['user', 'label']),
        ]


class Category(models.Model):
    """Categories for organizing transactions"""
    label = models.CharField(max_length=100, unique=True, db_index=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='categories')

    def __str__(self):
        return self.label

    class Meta:
        ordering = ['label']
        verbose_name_plural = "Categories"
        indexes = [
            models.Index(fields=['user', 'label']),
        ]


class Account(models.Model):
    """User accounts for tracking balances"""

    ACCOUNT_TYPE_CHOICES = [
        ('SAVINGS', 'SAVINGS'),
        ('CHECKING', 'CHECKING'),
        ('CREDIT_CARD', 'CREDIT_CARD'),
        ('CASH', 'CASH'),
    ]
    name = models.CharField(max_length=100, db_index=True)
    account_type = models.CharField(max_length=100, default='SAVINGS', choices=ACCOUNT_TYPE_CHOICES)
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    is_default = models.BooleanField(default=False, db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='accounts')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.user.username}"

    class Meta:
        ordering = ['name']
        unique_together = ['name', 'user']
        indexes = [
            models.Index(fields=['user', 'name']),
            models.Index(fields=['user', 'is_default']),
        ]

    @staticmethod
    def gain_income(pk, amount):
        Account.objects.filter(id=pk).update(balance=models.F('balance') + Decimal(amount))

    @staticmethod
    def make_expense(pk, amount):
        Account.objects.filter(id=pk).update(balance=models.F('balance') - Decimal(amount))


class Transaction(models.Model):
    """Individual transactions (income/expense)"""
    MODE_CHOICES = TransactionModeChoices.choices
    CURRENCY_CHOICES = TransactionCurrencyChoices.choices

    mode = models.CharField(max_length=10, choices=MODE_CHOICES, db_index=True)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='GHS', db_index=True)
    details = models.TextField(blank=True, null=True)
    reference = models.CharField(max_length=100, blank=True, null=True)

    # Foreign keys
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='transactions')
    destination_account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='incoming_transfers',
    )
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='transactions')
    tags = models.ManyToManyField(Tag, blank=True)

    # Attachment (receipt image or PDF)
    attachment = models.FileField(
        upload_to='receipts/%Y/%m/',
        blank=True,
        null=True,
        help_text='Receipt image (JPEG, PNG, WebP, GIF) or PDF',
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    transaction_time = models.DateTimeField(default=timezone.now, db_index=True)

    def __str__(self):
        return f"{self.get_mode_display()}: {self.currency} {self.amount} - {self.account.name}"

    @property
    def currency_symbol(self):
        return CURRENCY_SYMBOLS.get(self.currency, self.currency)

    @property
    def attachment_type(self):
        if not self.attachment:
            return None
        return 'pdf' if self.attachment.name.lower().endswith('.pdf') else 'image'

    @property
    def is_editable(self):
        return timezone.now() - self.created_at <= timedelta(hours=24)

    def save(self, *args, **kwargs):
        """Update account balance when transaction is saved"""

        if self.pk:
            # Editing existing transaction — reverse old impact, apply new
            old = Transaction.objects.get(pk=self.pk)
            # Reverse old balance impact
            if old.mode == 'INCOME':
                Account.make_expense(old.account.id, old.amount)
            elif old.mode == 'EXPENSE':
                Account.gain_income(old.account.id, old.amount)
            else:  # TRANSFER
                Account.gain_income(old.account.id, old.amount)
                if old.destination_account_id:
                    Account.make_expense(old.destination_account_id, old.amount)
            # Apply new balance impact
            if self.mode == 'INCOME':
                Account.gain_income(self.account.id, self.amount)
            elif self.mode == 'EXPENSE':
                Account.make_expense(self.account.id, self.amount)
            else:  # TRANSFER
                Account.make_expense(self.account.id, self.amount)
                if self.destination_account_id:
                    Account.gain_income(self.destination_account_id, self.amount)
        else:
            if self.mode == 'INCOME':
                Account.gain_income(self.account.id, self.amount)
            elif self.mode == 'EXPENSE':
                Account.make_expense(self.account.id, self.amount)
            else:  # TRANSFER
                Account.make_expense(self.account.id, self.amount)
                if self.destination_account_id:
                    Account.gain_income(self.destination_account_id, self.amount)

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Update account balance when transaction is deleted"""
        # Reverse the transaction's effect on balance
        if self.mode == 'INCOME':
            Account.make_expense(self.account.id, self.amount)
        elif self.mode == 'EXPENSE':
            Account.gain_income(self.account.id, self.amount)
        else:  # TRANSFER
            Account.gain_income(self.account.id, self.amount)
            if self.destination_account_id:
                Account.make_expense(self.destination_account_id, self.amount)

        super().delete(*args, **kwargs)

    class Meta:
        ordering = ['-transaction_time', 'account__name', 'amount', 'reference']
        indexes = [
            models.Index(fields=['-transaction_time', 'mode']),
            models.Index(fields=['account', '-transaction_time']),
            models.Index(fields=['category', '-transaction_time']),
            models.Index(fields=['mode', '-transaction_time', 'account']),
            models.Index(fields=['-transaction_time', 'account', 'mode']),
        ]


class RecurringFrequencyChoices(BaseChoices):
    DAILY = 'DAILY', 'Daily'
    WEEKLY = 'WEEKLY', 'Weekly'
    MONTHLY = 'MONTHLY', 'Monthly'
    QUARTERLY = 'QUARTERLY', 'Quarterly'
    YEARLY = 'YEARLY', 'Yearly'
    CUSTOM = 'CUSTOM', 'Custom'


class CustomRecurrenceTypeChoices(BaseChoices):
    DAYS_OF_WEEK = 'DAYS_OF_WEEK', 'Specific days of the week'
    DAYS_OF_MONTH = 'DAYS_OF_MONTH', 'Specific days of the month'


class RecurringOccurrenceStatusChoices(BaseChoices):
    PENDING = 'PENDING', 'Pending Approval'
    AUTO_CREATED = 'AUTO_CREATED', 'Auto Created'
    CONFIRMED = 'CONFIRMED', 'Confirmed'
    DISMISSED = 'DISMISSED', 'Dismissed'


def _add_months(anchor, months):
    """Add `months` calendar months to `anchor`, clamping the day to the target month's length."""
    month_index = anchor.month - 1 + months
    year = anchor.year + month_index // 12
    month = month_index % 12 + 1
    day = min(anchor.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


class RecurringTransaction(models.Model):
    """A schedule that periodically creates a Transaction, either automatically or after user approval."""
    FREQUENCY_CHOICES = RecurringFrequencyChoices.choices
    CUSTOM_TYPE_CHOICES = CustomRecurrenceTypeChoices.choices

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recurring_transactions')

    # Transaction template fields (mirrors Transaction)
    mode = models.CharField(max_length=10, choices=TransactionModeChoices.choices)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    currency = models.CharField(max_length=3, choices=TransactionCurrencyChoices.choices, default='GHS')
    details = models.TextField(blank=True, null=True)
    reference = models.CharField(max_length=100, blank=True, null=True)

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='recurring_transactions')
    destination_account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='incoming_recurring_transfers',
    )
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='recurring_transactions'
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name='recurring_transactions')

    # Scheduling
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, default=RecurringFrequencyChoices.YEARLY)
    custom_type = models.CharField(max_length=20, choices=CUSTOM_TYPE_CHOICES, blank=True, null=True)
    custom_weekdays = models.JSONField(default=list, blank=True, help_text='0=Monday .. 6=Sunday')
    custom_month_days = models.JSONField(default=list, blank=True, help_text='Day-of-month numbers, 1-31')

    renewal_date = models.DateField(default=timezone.localdate)
    next_run_date = models.DateField(db_index=True)
    end_date = models.DateField(blank=True, null=True)

    # Behaviour toggle: True = auto-create silently, False = notify for approval first
    is_auto_renew = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, db_index=True)

    # Short custom note appended to both the approval-request and auto-created
    # notifications for this schedule. Capped at standard SMS length (160 chars)
    # since it's meant to read fine even if these notifications are ever sent as SMS.
    notification_note = models.CharField(max_length=160, blank=True, null=True)

    last_run_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_mode_display()}: {self.currency} {self.amount} ({self.get_frequency_display()})"

    @property
    def currency_symbol(self):
        return CURRENCY_SYMBOLS.get(self.currency, self.currency)

    def _next_weekday_occurrence(self, after_date):
        weekdays = self.custom_weekdays or []
        if not weekdays:
            return None
        for offset in range(1, 8):
            candidate = after_date + timedelta(days=offset)
            if candidate.weekday() in weekdays:
                return candidate
        return None

    def _next_month_day_occurrence(self, after_date):
        month_days = sorted(set(self.custom_month_days or []))
        if not month_days:
            return None

        year, month = after_date.year, after_date.month
        for _ in range(25):  # safety cap, well over 2 years of months
            days_in_month = calendar.monthrange(year, month)[1]
            candidates = sorted({min(day, days_in_month) for day in month_days})
            for day in candidates:
                candidate = date(year, month, day)
                if candidate > after_date:
                    return candidate
            month += 1
            if month > 12:
                month = 1
                year += 1
        return None

    def next_occurrence(self, after_date):
        """First valid occurrence date strictly after `after_date`."""
        if self.frequency == RecurringFrequencyChoices.DAILY:
            return after_date + timedelta(days=1)
        if self.frequency == RecurringFrequencyChoices.WEEKLY:
            return after_date + timedelta(weeks=1)
        if self.frequency == RecurringFrequencyChoices.MONTHLY:
            return _add_months(after_date, 1)
        if self.frequency == RecurringFrequencyChoices.QUARTERLY:
            return _add_months(after_date, 3)
        if self.frequency == RecurringFrequencyChoices.YEARLY:
            return _add_months(after_date, 12)
        if self.frequency == RecurringFrequencyChoices.CUSTOM:
            if self.custom_type == CustomRecurrenceTypeChoices.DAYS_OF_WEEK:
                return self._next_weekday_occurrence(after_date)
            if self.custom_type == CustomRecurrenceTypeChoices.DAYS_OF_MONTH:
                return self._next_month_day_occurrence(after_date)
        return None

    def advance_next_run_date(self):
        """Advance next_run_date to the next occurrence; deactivate if that falls past end_date."""
        next_date = self.next_occurrence(self.next_run_date)
        if next_date is None or (self.end_date and next_date > self.end_date):
            self.is_active = False
            return
        self.next_run_date = next_date

    def _first_occurrence_on_or_after(self, anchor):
        """The earliest valid occurrence on/after `anchor`, per the current frequency rule."""
        if self.frequency == RecurringFrequencyChoices.CUSTOM:
            # `anchor` itself may not satisfy the day-of-week/day-of-month rule.
            return self.next_occurrence(anchor - timedelta(days=1)) or anchor
        # Simple periodic frequencies have no per-date constraint, so `anchor` itself qualifies.
        return anchor

    def reschedule(self, anchor=None):
        """
        Recompute next_run_date from scratch (used when an edit changes frequency/custom
        rules — the next run should reflect the edit; already-created occurrences are untouched).
        """
        anchor = anchor or timezone.localdate()
        self.next_run_date = self._first_occurrence_on_or_after(anchor)
        if self.end_date and self.next_run_date > self.end_date:
            self.is_active = False

    def save(self, *args, **kwargs):
        if not self.next_run_date:
            self.next_run_date = self._first_occurrence_on_or_after(self.renewal_date)
            if self.end_date and self.next_run_date > self.end_date:
                self.is_active = False
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['next_run_date']
        indexes = [
            models.Index(fields=['is_active', 'next_run_date']),
            models.Index(fields=['user', 'is_active']),
        ]


class RecurringTransactionOccurrence(models.Model):
    """One due date for a RecurringTransaction; tracks how it was resolved."""
    recurring_transaction = models.ForeignKey(RecurringTransaction, on_delete=models.CASCADE, related_name='occurrences')
    scheduled_date = models.DateField(db_index=True)
    status = models.CharField(
        max_length=20,
        choices=RecurringOccurrenceStatusChoices.choices,
        default=RecurringOccurrenceStatusChoices.PENDING,
        db_index=True,
    )
    transaction = models.OneToOneField(
        Transaction, on_delete=models.SET_NULL, null=True, blank=True, related_name='recurring_occurrence'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.recurring_transaction} — {self.scheduled_date} ({self.status})"

    class Meta:
        ordering = ['-scheduled_date']
        unique_together = ('recurring_transaction', 'scheduled_date')
