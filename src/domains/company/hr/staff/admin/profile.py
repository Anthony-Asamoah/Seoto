from django.contrib import admin

from ..models import Certificate, Education, Hobby, JobExperience, Specialisation


class EducationInline(admin.StackedInline):
    model = Education
    extra = 0
    fields = (
        ('school', 'city'),
        ('certificate_title', 'certificate_type', 'other_certificate_type'),
        ('start_date', 'end_date'),
        'description',
        ('order', 'hidden'),
    )


class CertificateInline(admin.StackedInline):
    model = Certificate
    extra = 0
    fields = (
        ('course_name', 'issuing_body'),
        ('reference', 'is_sponsored'),
        ('awarded_on', 'expires_on'),
        'description',
        ('order', 'hidden'),
    )


class JobExperienceInline(admin.StackedInline):
    model = JobExperience
    extra = 0
    fields = (
        ('job_title', 'employer', 'city'),
        ('start_date', 'end_date'),
        'description',
        ('order', 'hidden'),
    )


class SpecialisationInline(admin.TabularInline):
    model = Specialisation
    extra = 0
    fields = ('name', 'tools', 'is_active', 'order', 'hidden')


class HobbyInline(admin.TabularInline):
    model = Hobby
    extra = 0
    fields = ('description', 'order', 'hidden')


class ProfileSectionAdmin(admin.ModelAdmin):
    """shared list config for the ordered, hideable profile records"""
    list_filter = ('hidden',)
    autocomplete_fields = ('member',)
    search_fields = ('member__staff_id', 'member__user__first_name', 'member__user__last_name')


class EducationAdmin(ProfileSectionAdmin):
    list_display = ('member', 'certificate_title', 'school', 'start_date', 'end_date', 'hidden')
    list_filter = ('certificate_type', 'hidden')
    search_fields = ProfileSectionAdmin.search_fields + ('school', 'certificate_title')


class CertificateAdmin(ProfileSectionAdmin):
    list_display = ('member', 'course_name', 'issuing_body', 'awarded_on', 'expires_on', 'is_sponsored')
    list_filter = ('is_sponsored', 'hidden')
    search_fields = ProfileSectionAdmin.search_fields + ('course_name', 'issuing_body')


class JobExperienceAdmin(ProfileSectionAdmin):
    list_display = ('member', 'job_title', 'employer', 'start_date', 'end_date', 'hidden')
    search_fields = ProfileSectionAdmin.search_fields + ('job_title', 'employer')


class SpecialisationAdmin(ProfileSectionAdmin):
    list_display = ('member', 'name', 'is_active', 'order', 'hidden')
    list_filter = ('is_active', 'hidden')
    search_fields = ProfileSectionAdmin.search_fields + ('name', 'tools')


class HobbyAdmin(ProfileSectionAdmin):
    list_display = ('member', 'description', 'order', 'hidden')
    search_fields = ProfileSectionAdmin.search_fields + ('description',)


admin.site.register(Education, EducationAdmin)
admin.site.register(Certificate, CertificateAdmin)
admin.site.register(JobExperience, JobExperienceAdmin)
admin.site.register(Specialisation, SpecialisationAdmin)
admin.site.register(Hobby, HobbyAdmin)
