from django.urls import path
from django.contrib.auth import views
from .views import (
	register, profile, totp_setup_confirm, totp_setup_done,
	CustomLoginView, CustomPasswordResetView,
)
from .forms import CustomPasswordChangeForm, CustomSetPasswordForm


urlpatterns = [
	path("login/", CustomLoginView.as_view(), name='login'),
	path("logout/", views.LogoutView.as_view(), name="logout"),
	path(
		"password_change/", views.PasswordChangeView.as_view(template_name='accounts/password_change.html', form_class=CustomPasswordChangeForm), name="password_change"
	),
	path(
		"password_change/done/",
		views.PasswordChangeDoneView.as_view(template_name='accounts/password_changed.html'),
		name="password_change_done",
	),
	path("password_reset/", CustomPasswordResetView.as_view(), name="password_reset"),
	path(
		"password_reset/done/",
		views.PasswordResetDoneView.as_view(template_name='accounts/password_sent.html'),
		name="password_reset_done",
	),
	path(
		"reset/<uidb64>/<token>/",
		views.PasswordResetConfirmView.as_view(template_name='accounts/password_reset_confirm.html', form_class=CustomSetPasswordForm),
		name="password_reset_confirm",
	),
	path(
		"reset/done/",
		views.PasswordResetCompleteView.as_view(template_name='accounts/password_reset_complete.html'),
		name="password_reset_complete",
	),
	path('register', register, name='register'),
	# Both must stay above the username catch-all, and 'done' above the token pattern.
	path('2fa/setup/done/', totp_setup_done, name='totp_setup_done'),
	path('2fa/setup/<str:token>/', totp_setup_confirm, name='totp_setup_confirm'),
	path('<str:username>', profile, name='profile'),
]