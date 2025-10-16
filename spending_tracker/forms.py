from django import forms

from .models import Transaction, Account, Category


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['mode', 'amount', 'currency', 'details', 'reference', 'account', 'category', 'tags', 'transaction_time']
        widgets = {
            'transaction_time': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'details': forms.Textarea(attrs={'rows': 3}),
            'tags': forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user:
            self.fields['account'].queryset = Account.objects.filter(user=user)
            self.fields['category'].queryset = Category.objects.filter(user=user)


class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ['name', 'balance', 'account_type']
        widgets = {
            'balance': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['label', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2}),
        }
