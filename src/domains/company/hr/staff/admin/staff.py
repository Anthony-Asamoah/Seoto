from django import forms
from django.contrib import admin
from django.contrib.admin.widgets import AdminTextareaWidget
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import path, reverse
from django.utils import timezone

from infrastructure.utils.widgets import ImagePreviewInput

from ..models import Assignment, Member, Position
from .contact import AddressInline, ContactInline
from .profile import (
    CertificateInline,
    EducationInline,
    HobbyInline,
    JobExperienceInline,
    SpecialisationInline,
)
from .team import MembershipInline


class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.initial.setdefault('effective_from', timezone.localdate())
        # The row has no position yet on load, so the salary is filled in by JS on pick.
        # The admin wraps the select in a RelatedFieldWidgetWrapper whose attrs the inner
        # widget only sometimes aliases, so stamp the select itself.
        widget = self.fields['position'].widget
        widget = getattr(widget, 'widget', widget)
        widget.attrs['data-defaults-url'] = reverse('admin:company_staff_position_defaults')


class AssignmentInlineForm(AssignmentForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.skip_overlap_check = True


class AssignmentInlineFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()
        kept = []
        for form in self.forms:
            if not form.cleaned_data or form.cleaned_data.get('DELETE'):
                continue
            assignment = form.instance
            if not assignment.position_id or not assignment.effective_from:
                continue
            if any(assignment.overlaps(other) for other in kept):
                form.add_error('effective_from', Assignment.OVERLAP_ERROR)
            else:
                kept.append(assignment)


class AssignmentInline(admin.TabularInline):
    model = Assignment
    form = AssignmentInlineForm

    class Media:
        js = (
            'admin/js/vendor/jquery/jquery.js',
            'admin/js/jquery.init.js',
            'js/admin_assignment_defaults.js',
        )
    formset = AssignmentInlineFormSet
    extra = 0
    fields = ('position', 'salary', 'currency', 'effective_from', 'effective_to', 'note')
    autocomplete_fields = ('position',)


class MemberForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = '__all__'
        widgets = {
            'profile_image': ImagePreviewInput(crop=True),
            'about': AdminTextareaWidget(attrs={'rows': 4}),
        }
        labels = {'national_id': 'National ID'}
        help_texts = {
            'about': 'Shown on the marketing site profile.',
            'is_public': 'Only public members are eligible to appear on the marketing site.',
            'profile_image': 'Cropped to a square on upload.',
        }


class MemberAdmin(admin.ModelAdmin):
    form = MemberForm
    list_display = ('__str__', 'staff_id', 'current_position', 'started_on', 'ended_on', 'is_public')
    list_filter = ('is_public', 'gender', 'teams', 'assignments__position')
    search_fields = ('staff_id', 'user__first_name', 'user__last_name', 'user__username', 'user__email')
    autocomplete_fields = ('user',)
    date_hierarchy = 'started_on'
    inlines = (
        AssignmentInline, MembershipInline, ContactInline, AddressInline,
        EducationInline, CertificateInline, JobExperienceInline,
        SpecialisationInline, HobbyInline,
    )

    readonly_fields = ('staff_id',)

    fieldsets = (
        ('General', {
            'fields': (
                'user', 'staff_id', 'started_on', 'ended_on',
                'gender', 'date_of_birth', 'nationality', 'hometown', 'national_id',
                'profile_image', 'about', 'is_public',
            ),
        }),
    )

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj:
            return fieldsets
        # Nothing to show before the first save; the ID is issued on insert.
        first, *rest = fieldsets
        name, options = first
        options = {**options, 'fields': tuple(f for f in options['fields'] if f != 'staff_id')}
        return ((name, options), *rest)

    @admin.display(description='Positions')
    def current_position(self, obj):
        return ', '.join(str(position) for position in obj.positions) or '—'


class PositionAdmin(admin.ModelAdmin):
    list_display = ('name', 'reference_salary', 'currency', 'holders')
    search_fields = ('name', 'description')

    def get_urls(self):
        # Ahead of super(), or `<path:object_id>/change/` swallows this.
        custom_urls = [
            path(
                'defaults/',
                self.admin_site.admin_view(self.defaults_view),
                name='company_staff_position_defaults',
            ),
        ]
        return custom_urls + super().get_urls()

    def defaults_view(self, request):
        """feeds the assignment rows; admin_view() only proves staff, so check the perm here"""
        if not self.has_view_permission(request):
            raise PermissionDenied
        position = get_object_or_404(Position, pk=request.GET.get('position'))
        return JsonResponse({
            'salary': '' if position.reference_salary is None else str(position.reference_salary),
            'currency': position.currency,
        })

    @admin.display(description='Current holders')
    def holders(self, obj):
        return obj.assignments.current().values('member').distinct().count()


class AssignmentAdmin(admin.ModelAdmin):
    form = AssignmentForm
    list_display = ('member', 'position', 'salary', 'currency', 'effective_from', 'effective_to')
    list_filter = ('position', 'currency')
    search_fields = ('member__staff_id', 'member__user__first_name', 'member__user__last_name', 'position__name')
    autocomplete_fields = ('member', 'position')
    date_hierarchy = 'effective_from'

    class Media:
        js = (
            'admin/js/vendor/jquery/jquery.js',
            'admin/js/jquery.init.js',
            'js/admin_assignment_defaults.js',
        )


admin.site.register(Member, MemberAdmin)
admin.site.register(Position, PositionAdmin)
admin.site.register(Assignment, AssignmentAdmin)
