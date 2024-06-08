from django.contrib import admin

from .models import Message, Stack, Education, JobExperience, Intro


@admin.register(Intro)
class IntroAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "email",
        "first_name",
        "last_name",
        "phone",
        "country",
    )
    list_display_links = list_display
    ordering = ('id',)


@admin.register(Education)
class EducationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "school",
        "certificate_title",
        "certificate_type",
        "start_date",
        "end_date",
    )
    list_display_links = list_display
    ordering = ('id',)


@admin.register(JobExperience)
class JobExperienceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "job_title",
        "employer",
        "start_date",
        "end_date",
    )
    list_display_links = list_display
    ordering = ('id',)


@admin.register(Stack)
class StackAdmin(admin.ModelAdmin):
    list_display = ['id', 'is_active', 'label']
    list_display_links = ['label']
    list_editable = ['is_active']
    ordering = ['id']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'subject', 'message', 'replied']
    list_display_links = list_display[:-1]
    list_filter = ['replied', 'email']
    search_fields = ['email', 'subject', 'message', 'name']
    list_editable = ['replied']
    list_per_page = 20
