from django import forms

from .models import MealOrder


class MealOrderForm(forms.ModelForm):
    price = forms.DecimalField(required=True)
    location = forms.CharField(required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

    class Meta:
        model = MealOrder
        fields = [
            'meal',
            'price',
            'quantity',
            'location',
            'details',
        ]
        widgets = {
            'quantity': forms.NumberInput(attrs={'min': 1}),
            'details': forms.Textarea(
                attrs={'rows': 3, 'placeholder': 'Any extra details or delivery instructions (optional)'}),
        }

    def clean_quantity(self):
        qty = self.cleaned_data.get('quantity') or 1
        if qty < 1:
            raise forms.ValidationError('Quantity must be at least 1.')
        return qty
