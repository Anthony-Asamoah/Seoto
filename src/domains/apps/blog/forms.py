from django import forms
from django.forms import ModelMultipleChoiceField
from django_ckeditor_5.widgets import CKEditor5Widget

from .models import Post, PostTags, PostReadGroup
from .utils import pluralize_label, singularize_label


class TitleCaseGroupChoiceField(ModelMultipleChoiceField):
    """ModelMultipleChoiceField that displays group labels in title case."""
    def label_from_instance(self, obj):
        return obj.label.title()


class PostForm(forms.ModelForm):
    tags_input = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'tag-input',
            'placeholder': 'Enter tags separated by commas (e.g., thoughts, love, nature)'
        }),
        help_text='Enter tags separated by commas. Tags will be converted to lowercase automatically.'
    )

    allowed_users_input = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'users-input',
            'placeholder': 'Enter usernames separated by commas (e.g., tony48, quanChii, joelsyx)'
        }),
        help_text='Enter usernames separated by commas. Invalid usernames will be ignored.'
    )

    allowed_groups = TitleCaseGroupChoiceField(
        queryset=PostReadGroup.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'group-select'}),
        help_text="Select groups that can view this post if it's not public.",
    )

    class Meta:
        model = Post
        fields = ['title', 'content', 'is_public', 'allowed_groups']
        widgets = {
            'content': CKEditor5Widget(config_name='blog'),
        }
        help_texts = {
            'is_public': 'If unchecked, only you and users/groups you specify below can view this post.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pre-populate tags_input with existing tags if editing
        if self.instance.pk:
            existing_tags = ', '.join([tag.label for tag in self.instance.tags.all()])
            self.fields['tags_input'].initial = existing_tags

            # Pre-populate allowed_users_input with existing users
            existing_users = ', '.join([user.username for user in self.instance.allowed_users.all()])
            self.fields['allowed_users_input'].initial = existing_users

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
            # Handle tags
            self._save_tags(instance)
            # Handle allowed users
            self._save_allowed_users(instance)
            # Save M2M relationships
            self.save_m2m()
        return instance

    def _save_tags(self, instance):
        """Process tags_input and associate tags with the post"""
        tags_input = self.cleaned_data.get('tags_input', '')

        # Clear existing tags
        instance.tags.clear()

        if tags_input:
            # Split by comma, strip whitespace, convert to singular lowercase, and filter empty strings
            tag_labels = [singularize_label(tag.strip()) for tag in tags_input.split(',') if tag.strip()]

            for tag_label in tag_labels:
                # Get or create the tag
                tag, created = PostTags.objects.get_or_create(label=tag_label)
                instance.tags.add(tag)

    def _save_allowed_users(self, instance):
        """Process allowed_users_input and associate users with the post"""
        from django.contrib.auth.models import User

        users_input = self.cleaned_data.get('allowed_users_input', '')

        # Clear existing allowed users
        instance.allowed_users.clear()

        if users_input:
            # Split by comma, strip whitespace, and filter empty strings
            usernames = [username.strip() for username in users_input.split(',') if username.strip()]

            for username in usernames:
                try:
                    # Case-insensitive username lookup
                    user = User.objects.get(username__iexact=username)
                    instance.allowed_users.add(user)
                except User.DoesNotExist:
                    # Silently ignore invalid usernames
                    pass


class TagForm(forms.ModelForm):
    class Meta:
        model = PostTags
        fields = ['label']
