from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import todo, tracker


@login_required
def jotter(request):
	todo_list = todo.objects.all().filter(user=request.user)
	tracker_list = tracker.objects.all().filter(user=request.user)

	context = {
		'todo_list': todo_list,
		'tracker_list': tracker_list
	}

	return render(request, 'jotter/jotter.html', context)
