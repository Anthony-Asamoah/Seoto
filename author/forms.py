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
