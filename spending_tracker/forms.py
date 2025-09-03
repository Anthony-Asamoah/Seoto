from django import forms

from .models import Transaction, Account


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['mode', 'amount', 'currency', 'details', 'reference', 'account', 'category', 'tags']
        widgets = {
            'created_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'details': forms.Textarea(attrs={'rows': 3}),
            'tags': forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user:
            self.fields['account'].queryset = Account.objects.filter(user=user)


class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ['name', 'balance', 'account_type']
        widgets = {
            'balance': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }
