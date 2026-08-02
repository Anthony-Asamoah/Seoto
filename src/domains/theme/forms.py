from django import forms
from django.core.validators import RegexValidator

from .models import ThemePreset, UserTheme, ThemeRating

# Hex color validator
hex_color_validator = RegexValidator(
    regex=r'^#[0-9A-Fa-f]{6}$',
    message='Enter a valid hex color code (e.g., #007bff)'
)


class CustomizeThemeForm(forms.ModelForm):
    """
    Form for users to customize their personal theme colors.
    """
    custom_primary_color = forms.CharField(
        max_length=7,
        required=False,
        validators=[hex_color_validator],
        widget=forms.TextInput(attrs={
            'type': 'color',
            'class': 'form-control form-control-color',
            'title': 'Choose primary color'
        }),
        label='Primary Color'
    )
    custom_secondary_color = forms.CharField(
        max_length=7,
        required=False,
        validators=[hex_color_validator],
        widget=forms.TextInput(attrs={
            'type': 'color',
            'class': 'form-control form-control-color',
            'title': 'Choose secondary color'
        }),
        label='Secondary Color'
    )
    custom_background_color = forms.CharField(
        max_length=7,
        required=False,
        validators=[hex_color_validator],
        widget=forms.TextInput(attrs={
            'type': 'color',
            'class': 'form-control form-control-color',
            'title': 'Choose background color'
        }),
        label='Background Color'
    )
    custom_text_color = forms.CharField(
        max_length=7,
        required=False,
        validators=[hex_color_validator],
        widget=forms.TextInput(attrs={
            'type': 'color',
            'class': 'form-control form-control-color',
            'title': 'Choose text color'
        }),
        label='Text Color'
    )
    custom_navbar_bg = forms.CharField(
        max_length=7,
        required=False,
        validators=[hex_color_validator],
        widget=forms.TextInput(attrs={
            'type': 'color',
            'class': 'form-control form-control-color',
            'title': 'Choose navbar background color'
        }),
        label='Navbar Background'
    )
    custom_navbar_text = forms.CharField(
        max_length=7,
        required=False,
        validators=[hex_color_validator],
        widget=forms.TextInput(attrs={
            'type': 'color',
            'class': 'form-control form-control-color',
            'title': 'Choose navbar text color'
        }),
        label='Navbar Text'
    )
    custom_text_head_color = forms.CharField(
        max_length=7,
        required=False,
        validators=[hex_color_validator],
        widget=forms.TextInput(attrs={
            'type': 'color',
            'class': 'form-control form-control-color',
            'title': 'Choose headers and labels color'
        }),
        label='Headers & Labels'
    )

    # Button color fields
    custom_btn_success_bg = forms.CharField(
        max_length=7,
        required=False,
        validators=[hex_color_validator],
        widget=forms.TextInput(attrs={
            'type': 'color',
            'class': 'form-control form-control-color',
            'title': 'Choose success button background'
        }),
        label='Success Button BG'
    )
    custom_btn_success_text = forms.CharField(
        max_length=7,
        required=False,
        validators=[hex_color_validator],
        widget=forms.TextInput(attrs={
            'type': 'color',
            'class': 'form-control form-control-color',
            'title': 'Choose success button text'
        }),
        label='Success Button Text'
    )
    custom_btn_danger_bg = forms.CharField(
        max_length=7,
        required=False,
        validators=[hex_color_validator],
        widget=forms.TextInput(attrs={
            'type': 'color',
            'class': 'form-control form-control-color',
            'title': 'Choose danger button background'
        }),
        label='Danger Button BG'
    )
    custom_btn_danger_text = forms.CharField(
        max_length=7,
        required=False,
        validators=[hex_color_validator],
        widget=forms.TextInput(attrs={
            'type': 'color',
            'class': 'form-control form-control-color',
            'title': 'Choose danger button text'
        }),
        label='Danger Button Text'
    )
    custom_btn_warning_bg = forms.CharField(
        max_length=7,
        required=False,
        validators=[hex_color_validator],
        widget=forms.TextInput(attrs={
            'type': 'color',
            'class': 'form-control form-control-color',
            'title': 'Choose warning button background'
        }),
        label='Warning Button BG'
    )
    custom_btn_warning_text = forms.CharField(
        max_length=7,
        required=False,
        validators=[hex_color_validator],
        widget=forms.TextInput(attrs={
            'type': 'color',
            'class': 'form-control form-control-color',
            'title': 'Choose warning button text'
        }),
        label='Warning Button Text'
    )
    custom_btn_info_bg = forms.CharField(
        max_length=7,
        required=False,
        validators=[hex_color_validator],
        widget=forms.TextInput(attrs={
            'type': 'color',
            'class': 'form-control form-control-color',
            'title': 'Choose info button background'
        }),
        label='Info Button BG'
    )
    custom_btn_info_text = forms.CharField(
        max_length=7,
        required=False,
        validators=[hex_color_validator],
        widget=forms.TextInput(attrs={
            'type': 'color',
            'class': 'form-control form-control-color',
            'title': 'Choose info button text'
        }),
        label='Info Button Text'
    )
    custom_btn_secondary_bg = forms.CharField(
        max_length=7,
        required=False,
        validators=[hex_color_validator],
        widget=forms.TextInput(attrs={
            'type': 'color',
            'class': 'form-control form-control-color',
            'title': 'Choose secondary button background'
        }),
        label='Secondary Button BG'
    )
    custom_btn_secondary_text = forms.CharField(
        max_length=7,
        required=False,
        validators=[hex_color_validator],
        widget=forms.TextInput(attrs={
            'type': 'color',
            'class': 'form-control form-control-color',
            'title': 'Choose secondary button text'
        }),
        label='Secondary Button Text'
    )

    # Card color fields
    custom_card_bg_color = forms.CharField(
        max_length=7,
        required=False,
        validators=[hex_color_validator],
        widget=forms.TextInput(attrs={
            'type': 'color',
            'class': 'form-control form-control-color',
            'title': 'Choose card background'
        }),
        label='Card Background'
    )
    custom_card_header_bg_color = forms.CharField(
        max_length=7,
        required=False,
        validators=[hex_color_validator],
        widget=forms.TextInput(attrs={
            'type': 'color',
            'class': 'form-control form-control-color',
            'title': 'Choose card header background'
        }),
        label='Card Header BG'
    )
    custom_card_text_color = forms.CharField(
        max_length=7,
        required=False,
        validators=[hex_color_validator],
        widget=forms.TextInput(attrs={
            'type': 'color',
            'class': 'form-control form-control-color',
            'title': 'Choose card text color'
        }),
        label='Card Text'
    )

    class Meta:
        model = UserTheme
        fields = [
            'custom_primary_color',
            'custom_secondary_color',
            'custom_background_color',
            'custom_text_color',
            'custom_text_head_color',
            'custom_navbar_bg',
            'custom_navbar_text',
            'custom_btn_success_bg',
            'custom_btn_success_text',
            'custom_btn_danger_bg',
            'custom_btn_danger_text',
            'custom_btn_warning_bg',
            'custom_btn_warning_text',
            'custom_btn_info_bg',
            'custom_btn_info_text',
            'custom_btn_secondary_bg',
            'custom_btn_secondary_text',
            'custom_card_bg_color',
            'custom_card_header_bg_color',
            'custom_card_text_color',
        ]


class PublishThemeForm(forms.Form):
    """
    Form for users to publish their custom theme to the public gallery.
    """
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter a unique name for your theme'
        }),
        help_text='Give your theme a catchy, descriptive name'
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Describe your theme, what inspired it, or what makes it special'
        }),
        help_text='Optional: Tell others about your theme (max 500 characters)',
        max_length=500
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean_name(self):
        """Ensure theme name is unique among user's published themes"""
        name = self.cleaned_data.get('name')
        if self.user:
            existing = ThemePreset.objects.filter(
                created_by=self.user,
                name__iexact=name
            ).exists()
            if existing:
                raise forms.ValidationError(
                    'You already have a published theme with this name. Please choose a different name.'
                )
        return name


class PresetForm(forms.ModelForm):
    """
    Form for admin to create official theme presets.
    """
    primary_color = forms.CharField(
        max_length=7,
        validators=[hex_color_validator],
        widget=forms.TextInput(attrs={
            'type': 'color',
            'class': 'form-control form-control-color'
        })
    )
    secondary_color = forms.CharField(
        max_length=7,
        validators=[hex_color_validator],
        widget=forms.TextInput(attrs={
            'type': 'color',
            'class': 'form-control form-control-color'
        })
    )
    background_color = forms.CharField(
        max_length=7,
        validators=[hex_color_validator],
        widget=forms.TextInput(attrs={
            'type': 'color',
            'class': 'form-control form-control-color'
        })
    )
    text_color = forms.CharField(
        max_length=7,
        validators=[hex_color_validator],
        widget=forms.TextInput(attrs={
            'type': 'color',
            'class': 'form-control form-control-color'
        })
    )
    navbar_bg = forms.CharField(
        max_length=7,
        validators=[hex_color_validator],
        widget=forms.TextInput(attrs={
            'type': 'color',
            'class': 'form-control form-control-color'
        })
    )
    navbar_text = forms.CharField(
        max_length=7,
        validators=[hex_color_validator],
        widget=forms.TextInput(attrs={
            'type': 'color',
            'class': 'form-control form-control-color'
        })
    )
    text_head_color = forms.CharField(
        max_length=7,
        validators=[hex_color_validator],
        widget=forms.TextInput(attrs={
            'type': 'color',
            'class': 'form-control form-control-color'
        })
    )
    btn_success_bg = forms.CharField(
        max_length=7,
        validators=[hex_color_validator],
        widget=forms.TextInput(attrs={
            'type': 'color',
            'class': 'form-control form-control-color'
        })
    )
    btn_success_text = forms.CharField(
        max_length=7,
        validators=[hex_color_validator],
        widget=forms.TextInput(attrs={
            'type': 'color',
            'class': 'form-control form-control-color'
        })
    )
    btn_danger_bg = forms.CharField(
        max_length=7,
        validators=[hex_color_validator],
        widget=forms.TextInput(attrs={
            'type': 'color',
            'class': 'form-control form-control-color'
        })
    )
    btn_danger_text = forms.CharField(
        max_length=7,
        validators=[hex_color_validator],
        widget=forms.TextInput(attrs={
            'type': 'color',
            'class': 'form-control form-control-color'
        })
    )
    btn_warning_bg = forms.CharField(
        max_length=7,
        validators=[hex_color_validator],
        widget=forms.TextInput(attrs={
            'type': 'color',
            'class': 'form-control form-control-color'
        })
    )
    btn_warning_text = forms.CharField(
        max_length=7,
        validators=[hex_color_validator],
        widget=forms.TextInput(attrs={
            'type': 'color',
            'class': 'form-control form-control-color'
        })
    )
    btn_info_bg = forms.CharField(
        max_length=7,
        validators=[hex_color_validator],
        widget=forms.TextInput(attrs={
            'type': 'color',
            'class': 'form-control form-control-color'
        })
    )
    btn_info_text = forms.CharField(
        max_length=7,
        validators=[hex_color_validator],
        widget=forms.TextInput(attrs={
            'type': 'color',
            'class': 'form-control form-control-color'
        })
    )
    btn_secondary_bg = forms.CharField(
        max_length=7,
        validators=[hex_color_validator],
        widget=forms.TextInput(attrs={
            'type': 'color',
            'class': 'form-control form-control-color'
        })
    )
    btn_secondary_text = forms.CharField(
        max_length=7,
        validators=[hex_color_validator],
        widget=forms.TextInput(attrs={
            'type': 'color',
            'class': 'form-control form-control-color'
        })
    )
    card_bg_color = forms.CharField(
        max_length=7,
        validators=[hex_color_validator],
        widget=forms.TextInput(attrs={
            'type': 'color',
            'class': 'form-control form-control-color'
        })
    )
    card_header_bg_color = forms.CharField(
        max_length=7,
        validators=[hex_color_validator],
        widget=forms.TextInput(attrs={
            'type': 'color',
            'class': 'form-control form-control-color'
        })
    )
    card_text_color = forms.CharField(
        max_length=7,
        validators=[hex_color_validator],
        widget=forms.TextInput(attrs={
            'type': 'color',
            'class': 'form-control form-control-color'
        })
    )

    class Meta:
        model = ThemePreset
        fields = [
            'name',
            'description',
            'primary_color',
            'secondary_color',
            'background_color',
            'text_color',
            'text_head_color',
            'navbar_bg',
            'navbar_text',
            'btn_success_bg',
            'btn_success_text',
            'btn_danger_bg',
            'btn_danger_text',
            'btn_warning_bg',
            'btn_warning_text',
            'btn_info_bg',
            'btn_info_text',
            'btn_secondary_bg',
            'btn_secondary_text',
            'card_bg_color',
            'card_header_bg_color',
            'card_text_color',
            'is_official',
            'is_featured'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class RatingForm(forms.ModelForm):
    """
    Form for users to rate a theme preset.
    """
    RATING_CHOICES = [(i, f'{i} Star{"s" if i > 1 else ""}') for i in range(1, 6)]

    rating = forms.ChoiceField(
        choices=RATING_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'rating-radio'}),
        label='Your Rating'
    )

    class Meta:
        model = ThemeRating
        fields = ['rating']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.theme = kwargs.pop('theme', None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.user = self.user
        if self.theme:
            instance.theme = self.theme
        if commit:
            instance.save()
        return instance
