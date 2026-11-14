from django.contrib import admin
from unfold.admin import ModelAdmin, StackedInline

from .models import ConsultationBooking, ConsultationRequest


class ReadOnlyAdminMixin:
    """Rows are written once by the public API; the admin only reads (and may purge spam)."""

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields]


class ConsultationBookingInline(ReadOnlyAdminMixin, StackedInline):
    model = ConsultationBooking
    can_delete = False
    extra = 0


class ConsultationRequestAdmin(ReadOnlyAdminMixin, ModelAdmin):
    list_display = ('created_at', 'kind', 'name', 'email', 'phone', 'interest', 'booked_for')
    list_filter = ('kind', 'created_at', 'interest')
    list_select_related = ('booking',)
    search_fields = ('name', 'email', 'company', 'phone', 'message')
    date_hierarchy = 'created_at'
    inlines = (ConsultationBookingInline,)

    @admin.display(description='Booked for', ordering='booking__start_time')
    def booked_for(self, obj):
        booking = getattr(obj, 'booking', None)
        if booking is None or not booking.is_booked:
            return '—'
        return booking.start_time or 'Booked (time unknown)'


class ConsultationBookingAdmin(ReadOnlyAdminMixin, ModelAdmin):
    list_display = ('consultation', 'provider', 'start_time', 'booked_at')
    list_filter = ('provider', 'start_time')
    list_select_related = ('consultation',)
    search_fields = ('consultation__name', 'consultation__email', 'event_uri', 'invitee_uri')


admin.site.register(ConsultationRequest, ConsultationRequestAdmin)
admin.site.register(ConsultationBooking, ConsultationBookingAdmin)
