"""HR routes — mounted at /api/company/hr/ by domains.company.urls."""
from django.urls import include, path

urlpatterns = [
    path('members/', include('domains.company.hr.staff.urls')),
]
