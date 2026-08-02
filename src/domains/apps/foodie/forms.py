from django import forms

from .models import meal


class UserMealForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
        self.fields['is_public'].widget.attrs['class'] = 'form-check-input'
        self.fields['is_fancy'].widget.attrs['class'] = 'form-check-input'

    class Meta:
        model = meal
        fields = [
            'name', 'description', 'cooking_duration',
            'ingredients', 'nutrients', 'benefits',
            'main_img', 'img_1', 'img_2', 'img_3',
            'is_public', 'is_fancy',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'ingredients': forms.Textarea(attrs={'rows': 3}),
            'nutrients': forms.Textarea(attrs={'rows': 3}),
            'benefits': forms.Textarea(attrs={'rows': 3}),
        }
