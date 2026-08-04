import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView, PasswordResetView
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404

from . import services
from .forms import RegisterForm, LoginForm, CustomPasswordResetForm
from .models import user_profile
from .utils import trigger_user_onboarded_email


class CustomLoginView(LoginView):
    """Custom login view that passes request to form for reCAPTCHA verification."""
    template_name = 'accounts/login.html'
    authentication_form = LoginForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs


class CustomPasswordResetView(PasswordResetView):
    """Custom password reset view that passes request to form for reCAPTCHA verification."""
    template_name = 'accounts/password_reset.html'
    form_class = CustomPasswordResetForm
    email_template_name = 'emails/password_reset_body.txt'
    html_email_template_name = 'emails/password_reset.html'
    subject_template_name = 'emails/password_reset_subject.txt'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST, request=request)
        if form.is_valid():
            form.cleaned_data['first_name'] = form.cleaned_data['first_name'].title()
            form.cleaned_data['last_name'] = form.cleaned_data['last_name'].title()
            user = form.save()
            messages.success(request, "Registration Complete")

            try:
                trigger_user_onboarded_email(user)
            except:
                logging.exception("Failed to send user onboarding email")

            return redirect('login')
    else:
        form = RegisterForm(request=request)
    return render(request, 'accounts/register.html', {'form': form})


def totp_setup_confirm(request, token):
    """Enrolment page behind the emailed link: scan the QR, then prove it works.

    Deliberately open to anonymous visitors, like password reset — the signed token is the
    credential, and the device it points at grants nothing until this page confirms it.
    """
    device = services.read_setup_token(token)
    if device is None:
        return render(request, 'accounts/totp_setup.html', {'valid_link': False})

    error = None
    if request.method == 'POST':
        # django-otp throttles the device itself, so repeated wrong codes back off here.
        if services.confirm_device(device, request.POST.get('code', '').strip()):
            return redirect('totp_setup_done')
        error = 'That code did not match. Check your authenticator app and try again.'

    return render(request, 'accounts/totp_setup.html', {
        'valid_link': True,
        'account': device.user,
        'qr_svg': services.qr_svg(device.config_url),
        'secret': services.secret_b32(device),
        'backup_codes': services.backup_codes(device.user),
        'error': error,
    })


def totp_setup_done(request):
    return render(request, 'accounts/totp_setup_done.html')


@login_required
def profile(request, username):
    user = get_object_or_404(User, username=username)

    context = {
        'user': user,
        'joined_day': user.date_joined.strftime('%A'),
        'joined_date': user.date_joined.strftime('%d %B %Y'),
        'joined_time': user.date_joined.strftime('%I:%M:%S %p'),
    }
    try:
        extra_info = user_profile.objects.get(user=user)
        context.update({'extra': extra_info})

    except Exception as e:
        logging.info(f'Additional info not found, Log: {e}')
        extra_info = False

    if request.method == 'POST':
        user.first_name = request.POST['first_name']
        user.last_name = request.POST['last_name']
        user.email = request.POST['email']

        contact = request.POST['contact']
        try:
            picture = request.FILES['picture']
        except Exception as e:
            logging.debug(f'Error at: {e}')
            picture = request.POST['picture']

        if extra_info:
            extra_info.user = user
            if contact:
                extra_info.contact = contact
            if picture:
                extra_info.picture = picture
        else:
            extra_info = user_profile.objects.create(
                user=user,
                contact=contact,
                picture=picture
            )

        with transaction.atomic():
            user.save()
            extra_info.save()
            messages.success(request, 'Details Updated')

        return redirect('profile', user.username)

    return render(request, 'accounts/profile.html', context)
