from django.contrib import admin
from django.utils import timezone

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


class MemberAdmin(admin.ModelAdmin):
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

    fieldsets = (
        (None, {
            'fields': ('user', 'staff_id', ('started_on', 'ended_on')),
        }),
        ('Personal', {
            'fields': ('gender', 'date_of_birth', 'nationality', 'hometown', 'national_id'),
        }),
        ('Public profile', {
            'fields': ('profile_image', 'about', 'is_public'),
            'description': 'Only public members are eligible to appear on the marketing site.',
        }),
    )

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
