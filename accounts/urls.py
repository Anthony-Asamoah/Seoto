from django.urls import path
from django.contrib.auth import views
from .views import register, profile


urlpatterns = [
	path("login/", views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
	path("logout/", views.LogoutView.as_view(), name="logout"),
	path(
		"password_change/", views.PasswordChangeView.as_view(), name="password_change"
	),
	path(
		"password_change/done/",
		views.PasswordChangeDoneView.as_view(template_name='accounts/password_changed.html'),
		name="password_change_done",
	),
	path("password_reset/", views.PasswordResetView.as_view(), name="password_reset"),
	path(
		"password_reset/done/",
		views.PasswordResetDoneView.as_view(template_name='accounts/password_sent.html'),
		name="password_reset_done",
	),
	path(
		"reset/<uidb64>/<token>/",
		views.PasswordResetConfirmView.as_view(),
		name="password_reset_confirm",
	),
	path(
		"reset/done/",
		views.PasswordResetCompleteView.as_view(),
		name="password_reset_complete",
	),
	path('register', register, name='register'),
	path('<str:username>', profile, name='profile'),
]