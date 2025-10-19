from django import forms
from django.utils import timezone

from .models import Transaction, Account, Category


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['mode', 'amount', 'currency', 'details', 'reference', 'account', 'category', 'tags', 'transaction_time']
        widgets = {
            'transaction_time': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local',
                    'class': 'form-control',
                    'step': '60',  # Allow minute-level precision
                },
                format='%Y-%m-%dT%H:%M'
            ),
            'details': forms.Textarea(attrs={'rows': 3}),
            'tags': forms.CheckboxSelectMultiple(),
        }
        labels = {
            'transaction_time': 'Transaction Date & Time',
        }
        help_texts = {
            'transaction_time': 'When did this transaction occur? Defaults to now.',
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user:
            self.fields['account'].queryset = Account.objects.filter(user=user)
            self.fields['category'].queryset = Category.objects.filter(user=user)

        # Set default value for transaction_time to now if creating new transaction
        if not self.instance.pk:
            self.fields['transaction_time'].initial = timezone.now().strftime('%Y-%m-%dT%H:%M')

        # Make transaction_time field required
        self.fields['transaction_time'].required = True


class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ['name', 'account_type', 'is_default']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'account_type': forms.Select(attrs={'class': 'form-control'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['label', 'description']
        widgets = {
            'label': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }
