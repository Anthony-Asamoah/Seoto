from django import forms
from django.contrib import messages
from django.contrib.auth.models import User
from django.shortcuts import redirect
from django.template.response import TemplateResponse

from domains.company.hr.staff.models import Member
from infrastructure.utils.widgets import ImagePreviewInput

from . import services
from .models import user_profile


class AccountForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']


class AccountProfileForm(forms.ModelForm):
    class Meta:
        model = user_profile
        fields = ['contact', 'picture']
        widgets = {'picture': ImagePreviewInput}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        thumbnail = getattr(self.instance, 'picture_thumbnail', None)
        if thumbnail:
            self.fields['picture'].widget.thumbnail_url = thumbnail.url


class MemberSelfForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = ['profile_image', 'about', 'gender', 'date_of_birth', 'nationality', 'hometown']
        widgets = {
            'profile_image': ImagePreviewInput(crop=True),
            'about': forms.Textarea(attrs={'rows': 4}),
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }
        help_texts = {'about': 'Shown on the marketing site profile.'}


def staff_context(member):
    return {
        'assignments': member.assignments.select_related('position').order_by('-effective_from'),
        'memberships': member.memberships.select_related('team').order_by('-joined_on'),
        'contacts': member.contacts.active(),
        'addresses': member.addresses.active(),
        'education': member.education.filter(hidden=False),
        'certificates': member.certificates.filter(hidden=False),
        'job_experience': member.job_experience.filter(hidden=False),
        'specialisations': member.specialisations.filter(hidden=False, is_active=True),
        'hobbies': member.hobbies.filter(hidden=False),
    }


def my_account(request, admin_site):
    user = request.user
    profile, _ = user_profile.objects.get_or_create(user=user)
    bound = request.method == 'POST'
    user_form = AccountForm(request.POST if bound else None, instance=user)
    profile_form = AccountProfileForm(
        request.POST if bound else None, request.FILES if bound else None, instance=profile
    )
    member = Member.objects.filter(user=user).first()
    member_form = (
        MemberSelfForm(
            request.POST if bound else None, request.FILES if bound else None,
            instance=member, prefix='member',
        ) if member else None
    )
    forms_ = [f for f in (user_form, profile_form, member_form) if f]
    if bound and all(f.is_valid() for f in forms_):
        for f in forms_:
            f.save()
        messages.success(request, 'Your account was updated.')
        return redirect('admin:my_account')

    context = {
        **admin_site.each_context(request),
        'title': 'My account',
        'profile': profile,
        'user_form': user_form,
        'profile_form': profile_form,
        'member': member,
        'member_form': member_form,
        'media': sum((f.media for f in forms_), forms.Media(js=['js/csrf.js', 'js/admin_totp.js'])),
        **services.security_context(user),
        **(staff_context(member) if member else {}),
    }
    return TemplateResponse(request, 'admin/accounts/my_account.html', context)
