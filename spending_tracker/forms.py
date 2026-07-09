from django import forms
from django.utils import timezone
from django.utils.html import strip_tags

from .models import (
    Transaction, Account, Category, RecurringTransaction,
    RecurringFrequencyChoices, CustomRecurrenceTypeChoices,
)


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['mode', 'amount', 'currency', 'details', 'reference', 'account', 'destination_account', 'category', 'tags', 'transaction_time', 'attachment']
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
            self.fields['destination_account'].queryset = Account.objects.filter(user=user)
            self.fields['category'].queryset = Category.objects.filter(user=user)

        # Set default value for transaction_time to now if creating new transaction
        if not self.instance.pk:
            self.fields['transaction_time'].initial = timezone.now().strftime('%Y-%m-%dT%H:%M')

        # Make transaction_time field required
        self.fields['transaction_time'].required = True

    def clean(self):
        cleaned_data = super().clean()
        # Subclasses that drop `mode` from the visible fields (ConfirmOccurrenceForm) still
        # need this check to run, so fall back to whatever they stamped on the instance.
        mode = cleaned_data.get('mode') or self.instance.mode
        account = cleaned_data.get('account')
        destination_account = cleaned_data.get('destination_account')
        if mode == 'TRANSFER':
            if not destination_account:
                self.add_error('destination_account', 'A destination account is required for transfers.')
            elif destination_account == account:
                self.add_error('destination_account', 'Destination account must differ from source account.')
        return cleaned_data


class ConfirmOccurrenceForm(TransactionForm):
    """The transaction a due recurring occurrence is about to become, open for editing.

    The schedule is a template, not a contract: what the user confirms here can differ from
    it, and nothing written here touches the RecurringTransaction. `mode`, `currency` and
    `reference` are inherited rather than editable — changing them would make this a
    different transaction than the one the schedule asked for.
    """

    tags_input = forms.CharField(
        required=False,
        label='Tags',
        help_text='Comma-separated',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. food, daily'}),
    )

    class Meta(TransactionForm.Meta):
        # Inherit, don't redeclare: a fresh Meta would silently drop the datetime-local
        # widget, the labels and the help texts.
        fields = ['amount', 'transaction_time', 'account', 'destination_account', 'category',
                  'details', 'attachment']

    def __init__(self, *args, recurring_transaction=None, scheduled_date=None, **kwargs):
        self.recurring_transaction = recurring_transaction
        self.scheduled_date = scheduled_date
        super().__init__(*args, **kwargs)

        recurring = recurring_transaction
        if recurring is None:
            return

        # Carried on the instance so save(commit=False) already has them, and so clean()
        # can see the mode it needs to validate transfers.
        self.instance.mode = recurring.mode
        self.instance.currency = recurring.currency
        self.instance.reference = recurring.reference

        if recurring.mode != 'TRANSFER':
            del self.fields['destination_account']

        self.fields['amount'].widget.attrs.update({
            'class': 'aura-amount',
            'inputmode': 'decimal',
            'step': '0.01',
            'min': '0.01',
        })
        for name in ('account', 'destination_account', 'category', 'details', 'attachment'):
            if name in self.fields:
                self.fields[name].widget.attrs['class'] = 'form-control'

        if self.is_bound:
            return

        # Seed from the schedule only on first render — a re-rendered invalid form must
        # show what the user typed, not silently revert to the template's values.
        self.fields['amount'].initial = recurring.amount
        self.fields['account'].initial = recurring.account_id
        self.fields['category'].initial = recurring.category_id
        if 'destination_account' in self.fields:
            self.fields['destination_account'].initial = recurring.destination_account_id
        # `details` is Quill HTML on the schedule; this is a plain textarea, so flatten it.
        self.fields['details'].initial = strip_tags(recurring.details or '')
        self.fields['tags_input'].initial = ', '.join(tag.label for tag in recurring.tags.all())

        if scheduled_date:
            # The occurrence records the date it was due, keeping the current time of day.
            due = timezone.localtime().replace(
                year=scheduled_date.year, month=scheduled_date.month, day=scheduled_date.day
            )
            self.fields['transaction_time'].initial = due.strftime('%Y-%m-%dT%H:%M')


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


class RecurringTransactionForm(forms.ModelForm):
    WEEKDAY_CHOICES = [
        (0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'), (3, 'Thursday'),
        (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday'),
    ]

    custom_weekdays = forms.MultipleChoiceField(
        choices=WEEKDAY_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Days of the week',
    )
    custom_month_days_input = forms.CharField(
        required=False,
        label='Days of the month',
        help_text='Comma-separated day numbers, e.g. 1, 15',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 1, 15'}),
    )

    class Meta:
        model = RecurringTransaction
        fields = [
            'mode', 'amount', 'currency', 'details', 'reference',
            'account', 'destination_account', 'category', 'tags',
            'frequency', 'custom_type', 'custom_weekdays',
            'renewal_date', 'end_date', 'is_auto_renew', 'notification_note',
        ]
        widgets = {
            'mode': forms.Select(attrs={'class': 'form-control'}),
            'currency': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'account': forms.Select(attrs={'class': 'form-control'}),
            'destination_account': forms.Select(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'reference': forms.TextInput(attrs={'class': 'form-control'}),
            'renewal_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'frequency': forms.Select(attrs={'class': 'form-control'}),
            'custom_type': forms.Select(attrs={'class': 'form-control'}),
            'is_auto_renew': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'details': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'tags': forms.CheckboxSelectMultiple(),
            'notification_note': forms.Textarea(attrs={
                'rows': 2, 'class': 'form-control', 'maxlength': '160',
                'placeholder': "e.g. Don't forget to check the balance first",
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        if user:
            self.fields['account'].queryset = Account.objects.filter(user=user)
            self.fields['destination_account'].queryset = Account.objects.filter(user=user)
            self.fields['category'].queryset = Category.objects.filter(user=user)

        if not self.instance.pk:
            self.fields['renewal_date'].initial = timezone.localdate()
        else:
            # `custom_weekdays` is a real model field, so ModelForm.__init__ already populated
            # self.initial['custom_weekdays'] from the instance as a list of ints (via
            # model_to_dict) — that takes precedence over field.initial in BoundField.value(),
            # so it must be overwritten here (not just field.initial) to get the string values
            # this MultipleChoiceField's choices expect.
            self.initial['custom_weekdays'] = [str(d) for d in (self.instance.custom_weekdays or [])]
            self.fields['custom_month_days_input'].initial = ', '.join(
                str(d) for d in (self.instance.custom_month_days or [])
            )

    def clean_custom_weekdays(self):
        return [int(value) for value in self.cleaned_data.get('custom_weekdays', [])]

    def clean_custom_month_days_input(self):
        raw = self.cleaned_data.get('custom_month_days_input', '').strip()
        if not raw:
            return []
        days = []
        for part in raw.split(','):
            part = part.strip()
            if not part:
                continue
            if not part.isdigit() or not (1 <= int(part) <= 31):
                raise forms.ValidationError('Day-of-month values must be numbers between 1 and 31.')
            days.append(int(part))
        return sorted(set(days))

    def clean(self):
        cleaned_data = super().clean()
        mode = cleaned_data.get('mode')
        account = cleaned_data.get('account')
        destination_account = cleaned_data.get('destination_account')
        if mode == 'TRANSFER':
            if not destination_account:
                self.add_error('destination_account', 'A destination account is required for transfers.')
            elif destination_account == account:
                self.add_error('destination_account', 'Destination account must differ from source account.')

        frequency = cleaned_data.get('frequency')
        custom_type = cleaned_data.get('custom_type')
        if frequency == RecurringFrequencyChoices.CUSTOM:
            if not custom_type:
                self.add_error('custom_type', 'Choose how the custom schedule repeats.')
            elif custom_type == CustomRecurrenceTypeChoices.DAYS_OF_WEEK and not cleaned_data.get('custom_weekdays'):
                self.add_error('custom_weekdays', 'Select at least one day of the week.')
            elif custom_type == CustomRecurrenceTypeChoices.DAYS_OF_MONTH and not cleaned_data.get('custom_month_days_input'):
                self.add_error('custom_month_days_input', 'Enter at least one day of the month.')

        renewal_date = cleaned_data.get('renewal_date')
        end_date = cleaned_data.get('end_date')
        if renewal_date and end_date and end_date <= renewal_date:
            self.add_error('end_date', 'End date must be after the renewal date.')

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.custom_month_days = self.cleaned_data.get('custom_month_days_input', [])
        if commit:
            instance.save()
            self._save_m2m()
        return instance
