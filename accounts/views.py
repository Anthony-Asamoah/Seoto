from django.contrib.auth import login, authenticate
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User

from . forms import registerForm


def register(request):
    if request.method == 'POST':
        form = registerForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            check = User.objects.get(username=username)
            if check:
                # give error message; username already taken
                pass

            return redirect('index')
    else:
        form = registerForm()
    return render(request, 'accounts/register.html', {'form': form})


def profile(request, username):
    user = get_object_or_404(User, username=username)
    if request.method == 'POST':
        pass

    context = {
        'user': user,
        'joined_day': user.date_joined.strftime('%A'),
        'joined_date': user.date_joined.strftime('%d %B %Y'),
        'joined_time': user.date_joined.strftime('%I:%M:%S %p')
    }
    return render(request, 'accounts/profile.html', context)
