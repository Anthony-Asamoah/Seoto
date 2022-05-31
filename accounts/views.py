from django.contrib.auth import login, authenticate
from django.shortcuts import render, redirect

from . forms import registerForm


def register(request):
    if request.method == 'POST':
        form = registerForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=raw_password)
            login(request, user)
            return redirect('index')
    else:
        form = registerForm()
    return render(request, 'accounts/register.html', {'form': form})
