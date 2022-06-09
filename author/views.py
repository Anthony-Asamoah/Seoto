from django.shortcuts import render, redirect
from django.contrib import messages
from .models import contact_form


def about(request):
	user = request.user
	if user.is_authenticated:

		form = contact_form(initial={
			'name': f'{user.first_name.title()} {user.last_name.title()}',
			'email': user.email
		})
	else:
		form = contact_form()

	if request.method == 'POST':
		form = contact_form(request.POST)
		if form.is_valid():
			form.save()
			messages.success(request, 'Message Submitted.')
			return redirect('about')
		else:
			messages.error(request, 'Could not be submitted.')

	context = {
		'form': form,
	}
	return render(request, 'author/about.html', context)
