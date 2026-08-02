from django.urls import path
from . import views

app_name = 'theme'

urlpatterns = [
    # Main theme pages
    path('', views.theme_home, name='theme_home'),
    path('presets/', views.preset_list, name='preset_list'),
    path('presets/<int:preset_id>/', views.preset_detail, name='preset_detail'),
    path('presets/<int:preset_id>/apply/', views.apply_preset, name='apply_preset'),
    path('presets/<int:preset_id>/rate/', views.rate_theme, name='rate_theme'),

    # User customization
    path('customize/', views.customize_theme, name='customize'),
    path('publish/', views.publish_theme, name='publish'),

    # Admin views
    path('admin/create/', views.admin_create_preset, name='admin_create'),
    path('admin/verify/', views.admin_verify_queue, name='admin_verify_queue'),
    path('admin/verify/<int:preset_id>/', views.admin_verify_theme, name='admin_verify'),
    path('admin/reject/<int:preset_id>/', views.admin_reject_theme, name='admin_reject'),
    path('admin/feature/<int:preset_id>/', views.admin_toggle_featured, name='admin_toggle_featured'),
]
