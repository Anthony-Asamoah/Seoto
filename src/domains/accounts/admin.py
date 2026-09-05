import logging

from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.db.models import Exists, OuterRef
from django.http import HttpResponseForbidden, HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import path, reverse
from django.utils.html import format_html, mark_safe
from django_otp.plugins.otp_totp.models import TOTPDevice

from infrastructure.utils.widgets import ImagePreviewInput

from . import services
from .models import user_profile
from .utils import trigger_totp_setup_email

logger = logging.getLogger(__name__)


def avatar_tag(thumbnail):
    if thumbnail:
        return format_html(
            '<img src="{}" style="width:36px;height:36px;border-radius:50%;object-fit:cover;">',
            thumbnail.url
        )
    return mark_safe(
        '<span style="display:inline-flex;align-items:center;justify-content:center;'
        'width:36px;height:36px;border-radius:50%;background:#e9e9e9;font-size:18px;">👤</span>'
    )


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = user_profile
        fields = ['contact', 'picture']
        widgets = {'picture': ImagePreviewInput}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        thumbnail = getattr(self.instance, 'picture_thumbnail', None)
        if thumbnail:
            self.fields['picture'].widget.thumbnail_url = thumbnail.url


class UserProfileInline(admin.StackedInline):
    """The profile only ever makes sense next to its user, so it has no menu entry of its own."""

    model = user_profile
    form = UserProfileForm
    can_delete = False
    verbose_name_plural = 'Profile'
    fields = ['contact', 'picture']


admin.site.unregister(User)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['user_icon', 'username', 'email', 'first_name', 'last_name', 'is_staff', 'has_2fa']
    change_form_template = 'admin/accounts/user_change_form.html'
    inlines = [UserProfileInline]
    fieldsets = [
        (None, {'fields': ['username', 'password_actions', 'last_login', 'date_joined']}),
        ('Personal info', {'fields': ['first_name', 'last_name', 'email']}),
        ('Permissions', {
            'fields': ['is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'],
        }),
    ]
    readonly_fields = ['password_actions', 'last_login', 'date_joined']

    class Media:
        # csrf.js is loaded from the site shell, which the admin does not extend, so
        # window.csrfFetch only exists in here because of this line.
        js = ('js/csrf.js', 'js/admin_totp.js')

    def get_queryset(self, request):
        # Both display columns would otherwise cost a query per row.
        return super().get_queryset(request).select_related('user_profile').annotate(
            _has_2fa=Exists(TOTPDevice.objects.filter(user=OuterRef('pk'), confirmed=True))
        )

    def get_inline_instances(self, request, obj=None):
        # The profile hangs off a user that does not exist yet on the add form.
        return super().get_inline_instances(request, obj) if obj else []

    def get_urls(self):
        # Ahead of super(), or `<path:object_id>/change/` swallows these.
        custom_urls = [
            path(
                '<int:user_id>/totp-setup/',
                self.admin_site.admin_view(self.totp_setup_view),
                name='auth_user_totp_setup',
            ),
            path(
                '<int:user_id>/totp-setup/verify/',
                self.admin_site.admin_view(self.totp_verify_view),
                name='auth_user_totp_verify',
            ),
            path(
                '<int:user_id>/totp-setup/email/',
                self.admin_site.admin_view(self.totp_email_view),
                name='auth_user_totp_email',
            ),
        ]
        return custom_urls + super().get_urls()

    def change_view(self, request, object_id, form_url='', extra_context=None):
        user = self.get_object(request, object_id)
        extra_context = {**(extra_context or {}), 'totp_status': self._totp_status(user)}
        return super().change_view(request, object_id, form_url, extra_context)

    @admin.display(description='Password')
    def password_actions(self, obj):
        # The stored hash tells an admin nothing useful, so only the reset link is offered.
        if obj is None or not obj.pk:
            return '—'
        if not obj.has_usable_password():
            return mark_safe('<span class="text-muted">No usable password set.</span>')
        return format_html(
            '<a class="btn btn-sm btn-outline-secondary" href="{}">Reset password</a>',
            reverse('admin:auth_user_password_change', args=[obj.pk]),
        )

    @admin.display(description='2FA', boolean=True, ordering='_has_2fa')
    def has_2fa(self, obj):
        return obj._has_2fa

    @staticmethod
    def _totp_status(user):
        if user is None:
            return 'none'
        if services.has_confirmed_device(user):
            return 'active'
        return 'pending' if services.pending_device(user) else 'none'

    def _load_target(self, request, user_id):
        """The user being enrolled, or a response explaining why we won't.

        admin_view() only proves staff + a verified OTP device; it says nothing about
        whether this admin may edit users.
        """
        if request.method != 'POST':
            return None, HttpResponseNotAllowed(['POST'])
        if not request.user.has_perm('auth.change_user'):
            return None, HttpResponseForbidden('You may not change users.')
        return get_object_or_404(User, pk=user_id), None

    def totp_setup_view(self, request, user_id):
        user, denied = self._load_target(request, user_id)
        if denied:
            return denied

        if services.has_confirmed_device(user) and request.POST.get('confirm') != '1':
            return self._render_modal(request, user, needs_confirmation=True)

        device = services.pending_device(user)
        if device is None or request.POST.get('confirm') == '1' or request.POST.get('rotate') == '1':
            device = services.issue_totp_device(user)
            services.issue_backup_codes(user)

        return self._render_modal(request, user, device=device)

    def totp_verify_view(self, request, user_id):
        user, denied = self._load_target(request, user_id)
        if denied:
            return denied

        device = services.pending_device(user)
        if device is None:
            return JsonResponse({'ok': False, 'message': 'There is nothing waiting to be activated.'})

        if not services.confirm_device(device, request.POST.get('code', '').strip()):
            return JsonResponse({'ok': False, 'message': 'That code did not match. Try the next one.'})

        return JsonResponse({'ok': True, 'message': f'Two-factor authentication is now active for {user}.'})

    def totp_email_view(self, request, user_id):
        user, denied = self._load_target(request, user_id)
        if denied:
            return denied

        if not user.email:
            return JsonResponse({'ok': False, 'message': 'This user has no email address on file.'})

        device = services.pending_device(user)
        if device is None:
            return JsonResponse({'ok': False, 'message': 'There is nothing waiting to be activated.'})

        try:
            trigger_totp_setup_email(user, device)
        except Exception:
            logger.exception('Failed to send TOTP setup email to %s', user)
            return JsonResponse({'ok': False, 'message': 'The email could not be sent. Check the error log.'})

        return JsonResponse({'ok': True, 'message': f'Setup link sent to {user.email}.'})

    def _render_modal(self, request, user, device=None, needs_confirmation=False):
        context = {'account': user, 'needs_confirmation': needs_confirmation}
        if device is not None:
            context.update({
                'qr_svg': services.qr_svg(device.config_url),
                'secret': services.secret_b32(device),
                'backup_codes': services.backup_codes(user),
            })
        return render(request, 'admin/accounts/totp_setup_modal.html', context)

    @admin.display(description='')
    def user_icon(self, obj):
        try:
            return avatar_tag(obj.user_profile.picture_thumbnail)
        except user_profile.DoesNotExist:
            return avatar_tag(None)
