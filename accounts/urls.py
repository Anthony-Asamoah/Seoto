from django.urls import path
from django.contrib.auth import views
from .views import register, profile
from .forms import LoginForm, CustomPasswordChangeForm, CustomPasswordResetForm, CustomSetPasswordForm


urlpatterns = [
	path("login/", views.LoginView.as_view(template_name='accounts/login.html', authentication_form=LoginForm), name='login'),
	path("logout/", views.LogoutView.as_view(), name="logout"),
	path(
		"password_change/", views.PasswordChangeView.as_view(template_name='accounts/password_change.html', form_class=CustomPasswordChangeForm), name="password_change"
	),
	path(
		"password_change/done/",
		views.PasswordChangeDoneView.as_view(template_name='accounts/password_changed.html'),
		name="password_change_done",
	),
	path("password_reset/", views.PasswordResetView.as_view(template_name='accounts/password_reset.html', form_class=CustomPasswordResetForm), name="password_reset"),
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
	path('<str:username>', profile, name='profile'),
]