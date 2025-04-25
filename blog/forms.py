from django import forms

from .models import Post, PostTags


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'content', 'is_public', 'tags', 'allowed_groups', 'allowed_users']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'markdown-editor',
                'rows': 15,
                'placeholder': 'Write your post content using Markdown...'
            }),
            'tags': forms.SelectMultiple(attrs={
                'class': 'tag-select',
            }),
            'allowed_groups': forms.SelectMultiple(attrs={
                'class': 'group-select',
            }),
            'allowed_users': forms.SelectMultiple(attrs={
                'class': 'user-select',
            }),
        }
        help_texts = {
            'content': '''
                <p>Use Markdown for formatting:</p>
                <ul>
                    <li><strong>Bold</strong>: **text** or __text__</li>
                    <li><em>Italic</em>: *text* or _text_</li>
                    <li><strong>Headers</strong>: # Header 1, ## Header 2, etc.</li>
                    <li><strong>Links</strong>: [Link Text](URL)</li>
                    <li><strong>Images</strong>: ![Alt Text](URL)</li>
                    <li><strong>Lists</strong>: * item or 1. item</li>
                    <li><strong>Blockquotes</strong>: > quote</li>
                    <li><strong>Code</strong>: `inline code` or ```code block```</li>
                </ul>
            ''',
            'is_public': 'If unchecked, only you and users/groups you specify below can view this post.',
            'tags': 'Select tags to categorize your post.',
            'allowed_groups': 'Select groups that can view this post if it\'s not public.',
            'allowed_users': 'Select individual users who can view this post if it\'s not public.',
        }


class TagForm(forms.ModelForm):
    class Meta:
        model = PostTags
        fields = ['label']
