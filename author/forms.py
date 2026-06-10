from django import forms
from django.forms import ModelForm, TextInput

from seoto.mixins.views import HoneypotMixin, RecaptchaMixin
from author.models import Message


class ContactForm(RecaptchaMixin, HoneypotMixin, ModelForm):
    recaptcha_action = 'contact'

    class Meta:
        model = Message
        fields = ['name', 'email', 'subject', 'message']
        widgets = {
            'name': TextInput(attrs={'placeholder': 'First name & Last name'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


class DiscoveryCallForm(RecaptchaMixin, HoneypotMixin, ModelForm):
    """
    Discovery-call request form used on the /reach-out page.

    Adds business-context fields (what they're looking for, budget, timeline,
    organization, phone, availability) on top of the base Message model. These
    extra fields are not stored as separate columns — they're composed into the
    Message's ``subject`` and ``message`` on save, so the existing email-forward
    flow captures everything with no schema change.
    """
    recaptcha_action = 'contact'

    # Mirrors the homepage's three "decision path" entry points.
    INTEREST_CHOICES = [
        ('launch', 'Launch Fast — Website or CMS'),
        ('proven', 'Use Proven Software — Inventory, CRM or ERP'),
        ('custom', 'Build Something Custom'),
        ('unsure', "I'm not sure yet — help me decide"),
    ]
    BUDGET_CHOICES = [
        ('', 'Prefer to discuss on the call'),
        ('lt5k', 'Under $5,000'),
        ('5to15k', '$5,000 – $15,000'),
        ('15to50k', '$15,000 – $50,000'),
        ('50kplus', '$50,000+'),
        ('unsure', 'Not sure yet'),
    ]
    TIMELINE_CHOICES = [
        ('', 'Select a timeline'),
        ('asap', 'As soon as possible'),
        ('1to3', '1 – 3 months'),
        ('3to6', '3 – 6 months'),
        ('exploring', 'Just exploring for now'),
    ]

    company = forms.CharField(
        required=False, max_length=200, label='Organization',
        widget=forms.TextInput(attrs={'placeholder': 'Company or organization'}),
    )
    phone = forms.CharField(
        required=False, max_length=40, label='Phone',
        widget=forms.TextInput(attrs={'type': 'tel', 'placeholder': 'Best number to reach you'}),
    )
    interest = forms.ChoiceField(
        choices=INTEREST_CHOICES, label='What are you looking for?',
        widget=forms.RadioSelect,
    )
    budget = forms.ChoiceField(
        choices=BUDGET_CHOICES, required=False, label='Budget range',
        widget=forms.Select,
    )
    timeline = forms.ChoiceField(
        choices=TIMELINE_CHOICES, required=False, label='Timeline',
        widget=forms.Select,
    )
    availability = forms.CharField(
        required=False, max_length=200, label='Best times for a call',
        widget=forms.TextInput(attrs={'placeholder': 'e.g. weekday mornings'}),
    )

    class Meta:
        model = Message
        # 'subject' is composed in save(), so it is intentionally not a form input.
        fields = ['name', 'email', 'message']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Your full name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'you@company.com'}),
            'message': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Tell us about your goals, challenges, and what success looks like…',
            }),
        }

    def _label(self, choices, value):
        return dict(choices).get(value) or '—'

    def save(self, commit=True):
        instance = super().save(commit=False)
        cd = self.cleaned_data

        interest_label = self._label(self.INTEREST_CHOICES, cd.get('interest'))
        instance.subject = f'Discovery Call — {interest_label}'

        details = [f'Looking for: {interest_label}']
        if cd.get('company'):
            details.append(f"Organization: {cd['company']}")
        if cd.get('phone'):
            details.append(f"Phone: {cd['phone']}")
        if cd.get('budget'):
            details.append(f'Budget: {self._label(self.BUDGET_CHOICES, cd["budget"])}')
        if cd.get('timeline'):
            details.append(f'Timeline: {self._label(self.TIMELINE_CHOICES, cd["timeline"])}')
        if cd.get('availability'):
            details.append(f"Best times for a call: {cd['availability']}")

        instance.message = (
            '— Discovery call request —\n'
            + '\n'.join(details)
            + '\n\n— In their words —\n'
            + (cd.get('message') or '')
        )

        if commit:
            instance.save()
        return instance
