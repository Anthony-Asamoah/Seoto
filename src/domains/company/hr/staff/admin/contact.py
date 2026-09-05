from django.contrib import admin

from ..models import Address, Contact


class ContactInline(admin.TabularInline):
    model = Contact
    extra = 0
    fields = ('channel', 'value', 'usage', 'label', 'is_primary', 'is_active', 'is_public', 'verified_on')


class AddressInline(admin.StackedInline):
    model = Address
    extra = 0
    fields = (
        ('address_type', 'is_primary', 'is_active'),
        ('house_number', 'street'),
        ('city', 'region', 'country'),
        ('postal_code', 'digital_address'),
        ('latitude', 'longitude'),
    )


class ContactAdmin(admin.ModelAdmin):
    list_display = ('member', 'channel', 'value', 'usage', 'is_primary', 'is_active', 'is_public')
    list_filter = ('channel', 'usage', 'is_primary', 'is_active', 'is_public')
    search_fields = ('value', 'member__staff_id', 'member__user__first_name', 'member__user__last_name')
    autocomplete_fields = ('member',)


class AddressAdmin(admin.ModelAdmin):
    list_display = ('member', 'address_type', 'city', 'region', 'country', 'is_primary', 'is_active')
    list_filter = ('address_type', 'is_primary', 'is_active', 'country')
    search_fields = ('city', 'street', 'digital_address', 'member__staff_id')
    autocomplete_fields = ('member',)


admin.site.register(Contact, ContactAdmin)
admin.site.register(Address, AddressAdmin)
