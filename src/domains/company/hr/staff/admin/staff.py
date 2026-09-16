from django import forms
from django.contrib import admin
from django.contrib.admin.widgets import AdminTextareaWidget
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


class AssignmentInline(admin.TabularInline):
    model = Assignment
    extra = 0
    fields = ('position', 'salary', 'currency', 'effective_from', 'note')
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

    @admin.display(description='Position')
    def current_position(self, obj):
        return obj.position or '—'


class PositionAdmin(admin.ModelAdmin):
    list_display = ('name', 'reference_salary', 'currency', 'holders')
    search_fields = ('name', 'description')

    @admin.display(description='Current holders')
    def holders(self, obj):
        return obj.assignments.filter(effective_from__lte=timezone.localdate()).count()


class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('member', 'position', 'salary', 'currency', 'effective_from')
    list_filter = ('position', 'currency')
    search_fields = ('member__staff_id', 'member__user__first_name', 'member__user__last_name', 'position__name')
    autocomplete_fields = ('member', 'position')
    date_hierarchy = 'effective_from'


admin.site.register(Member, MemberAdmin)
admin.site.register(Position, PositionAdmin)
admin.site.register(Assignment, AssignmentAdmin)
