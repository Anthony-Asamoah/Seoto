from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from seoto.utils import BaseChoices


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

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    transaction_time = models.DateTimeField(default=timezone.now, db_index=True)

    def __str__(self):
        return f"{self.get_mode_display()}: {self.currency} {self.amount} - {self.account.name}"

    @property
    def currency_symbol(self):
        return CURRENCY_SYMBOLS.get(self.currency, self.currency)

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
