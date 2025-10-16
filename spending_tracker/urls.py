from django.urls import path

from . import views

app_name = 'spending_tracker'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('transactions/', views.transaction_list, name='transaction_list'),
    path('transactions/add/', views.add_transaction, name='add_transaction'),
    path('transactions/<int:pk>/delete/', views.delete_transaction, name='delete_transaction'),
    path('tags/add/', views.add_tag, name='add_tag'),
    path('categories/add/', views.add_category, name='add_category'),
    path('accounts/', views.add_account, name='add_account'),
    path('accounts/quick-add/', views.add_account_quick, name='add_account_quick'),
    path('accounts/<int:pk>/', views.account_detail, name='account_detail'),
    path('reports/', views.reports, name='reports'),
]
