from decimal import Decimal

from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.db import models


class Tag(models.Model):
    """Tags for categorizing transactions"""
    label = models.CharField(max_length=50, unique=True)
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


class Category(models.Model):
    """Categories for organizing transactions"""
    label = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='categories')

    def __str__(self):
        return self.label

    class Meta:
        ordering = ['label']
        verbose_name_plural = "Categories"


class Account(models.Model):
    """User accounts for tracking balances"""

    ACCOUNT_TYPE_CHOICES = [
        ('SAVINGS', 'SAVINGS'),
        ('CHECKING', 'CHECKING'),
        ('CREDIT_CARD', 'CREDIT_CARD'),
        ('CASH', 'CASH'),
    ]
    name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=100, default='SAVINGS', choices=ACCOUNT_TYPE_CHOICES)
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    is_default = models.BooleanField(default=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='accounts')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.user.username}"

    class Meta:
        ordering = ['name']
        unique_together = ['name', 'user']

    @staticmethod
    def gain_income(pk, amount):
        Account.objects.filter(id=pk).update(balance=models.F('balance') + Decimal(amount))

    @staticmethod
    def make_expense(pk, amount):
        Account.objects.filter(id=pk).update(balance=models.F('balance') - Decimal(amount))


class Transaction(models.Model):
    """Individual transactions (income/expense)"""

    MODE_CHOICES = [
        ('INCOME', 'INCOME'),
        ('EXPENSE', 'EXPENSE'),
    ]

    CURRENCY_CHOICES = [
        ('GHS', 'GHS'),
        ('USD', 'USD'),
        ('EUR', 'EUR'),
        ('GBP', 'GBP'),
    ]

    mode = models.CharField(max_length=10, choices=MODE_CHOICES)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='GHS')
    details = models.TextField(blank=True, null=True)
    reference = models.CharField(max_length=100, blank=True, null=True)

    # Foreign keys
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='transactions')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    tags = models.ManyToManyField(Tag, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    transaction_time = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.get_mode_display()}: {self.currency} {self.amount} - {self.account.name}"

    def save(self, *args, **kwargs):
        """Update account balance when transaction is saved"""

        if not self.pk:
            if self.mode == 'INCOME':
                Account.gain_income(self.account.id, self.amount)
            else:  # expense
                Account.make_expense(self.account.id, self.amount)

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Update account balance when transaction is deleted"""
        # Reverse the transaction's effect on balance
        if self.mode == 'INCOME':
            Account.make_expense(self.account.id, self.amount)
        else:  # expense
            Account.gain_income(self.account.id, self.amount)

        super().delete(*args, **kwargs)

    class Meta:
        ordering = ['-created_at', 'account__name', 'amount', 'reference']
