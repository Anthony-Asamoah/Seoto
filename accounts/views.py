from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.db import transaction
from .models import user_profile
from .forms import registerForm
from django.contrib import messages

import logging


def register(request):
    if request.method == 'POST':
        form = registerForm(request.POST)
        if form.is_valid():
            form.cleaned_data['first_name'] = form.cleaned_data['first_name'].title()
            form.cleaned_data['last_name'] = form.cleaned_data['last_name'].title()
            form.save()
            return redirect('login')
    else:
        form = registerForm()
    return render(request, 'accounts/register.html', {'form': form})


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
        logging.info(f'extra info present')
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
