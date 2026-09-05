from django.contrib import admin

from ..models import Membership, Team


class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 0
    fields = ('team', 'role', 'joined_on', 'left_on')
    autocomplete_fields = ('team',)


class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'team_lead', 'active_members', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    inlines = (MembershipInline,)
    exclude = ('members',)

    @admin.display(description='Lead')
    def team_lead(self, obj):
        return obj.lead or '—'

    @admin.display(description='Active members')
    def active_members(self, obj):
        return obj.memberships.active().count()


class MembershipAdmin(admin.ModelAdmin):
    list_display = ('member', 'team', 'role', 'joined_on', 'left_on')
    list_filter = ('role', 'team')
    search_fields = ('member__staff_id', 'member__user__first_name', 'member__user__last_name', 'team__name')
    autocomplete_fields = ('member', 'team')


admin.site.register(Team, TeamAdmin)
admin.site.register(Membership, MembershipAdmin)
