from django import forms
from django.forms import ModelForm, TextInput

from infrastructure.core.mixins.views import HoneypotMixin, RecaptchaMixin
from infrastructure.utils.profanity import contains_profanity
from infrastructure.utils import normalize_phone, validate_phone
from domains.author.models import Message


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

    Two modes:
    - Full (default): the discovery funnel — captures context, then sends the
      lead on to Calendly to self-book a consultation. Requires an email.
    - Quick (``quick_message`` set): a lightweight "no email" path for clients
      who don't use email and can't self-book. Collapses to name + phone +
      message; requires a phone so we can call them back instead.
    """
    recaptcha_action = 'contact'

    # Set by the front-end toggle. When truthy, the form runs in "quick"
    # (no-email, call-me-back) mode — see ``clean`` / ``save`` and the template.
    quick_message = forms.BooleanField(required=False, widget=forms.HiddenInput())

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
        ('', 'When do you want to start?'),
        ('asap', 'As soon as possible'),
        ('1to3', '1 – 3 months'),
        ('3to6', '3 – 6 months'),
        ('exploring', 'Just exploring for now'),
    ]

    # Email is optional at the field level; ``clean`` requires either an email
    # (full mode) or a phone (quick mode), so every lead is reachable somehow.
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'placeholder': 'you@company.com'}),
    )
    company = forms.CharField(
        required=False, max_length=200, label='Organization',
        widget=forms.TextInput(attrs={'placeholder': 'Company or organization'}),
    )
    phone = forms.CharField(
        required=False, max_length=40, label='Phone',
        widget=forms.TextInput(attrs={'type': 'tel', 'placeholder': 'e.g. 024 123 4567 or +1 415 555 2671'}),
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
        choices=TIMELINE_CHOICES, required=False, label='Project timeline',
        widget=forms.Select,
    )

    class Meta:
        model = Message
        # 'subject' is composed in save(), so it is intentionally not a form input.
        fields = ['name', 'email', 'message']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Your full name'}),
            'message': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Tell us about your goals, challenges, and what success looks like…',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # In quick mode the discovery-only fields are hidden, so don't enforce
        # them. Lower ``interest`` here (field-level ``required`` is checked
        # before ``clean`` runs); email/phone are reconciled in ``clean``.
        if self.is_bound and self._is_quick(self.data):
            self.fields['interest'].required = False

    @staticmethod
    def _is_quick(data):
        return str(data.get('quick_message', '')).strip().lower() in ('1', 'true', 'on', 'yes')

    def _label(self, choices, value):
        return dict(choices).get(value) or '—'

    def clean(self):
        cleaned = super().clean()
        quick = bool(cleaned.get('quick_message'))
        if quick:
            if not cleaned.get('phone'):
                self.add_error('phone', 'Add a phone number so we can call you back.')
        elif not cleaned.get('email'):
            self.add_error(
                'email',
                'Enter your email — or switch to “Send a quick message” to leave a phone number instead.',
            )
        return cleaned

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '')
        if phone:
            validate_phone(phone)
            return normalize_phone(phone)
        return phone

    def clean_message(self):
        message = self.cleaned_data.get('message', '')
        if contains_profanity(message):
            raise forms.ValidationError("We don't tolerate profanity.")
        return message

    def save(self, commit=True):
        instance = super().save(commit=False)
        cd = self.cleaned_data

        if cd.get('quick_message'):
            # No-email path: the only way back to them is the phone, so make the
            # subject shout it and lead the body with the call-back request.
            instance.email = cd.get('email') or ''
            instance.subject = f'Quick message — please call back — {instance.name}'
            details = [f"Phone: {cd['phone']}"]
            if cd.get('company'):
                details.append(f"Organization: {cd['company']}")
            instance.message = (
                '— Quick message (no email — please call back) —\n'
                + '\n'.join(details)
                + '\n\n— In their words —\n'
                + (cd.get('message') or '')
            )
            if commit:
                instance.save()
            return instance

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

        instance.message = (
            '— Discovery call request —\n'
            + '\n'.join(details)
            + '\n\n— In their words —\n'
            + (cd.get('message') or '')
        )

        if commit:
            instance.save()
        return instance
