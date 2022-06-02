from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User

from . forms import registerForm


def register(request):
    if request.method == 'POST':
        form = registerForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
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
