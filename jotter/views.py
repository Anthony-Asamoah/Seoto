from datetime import datetime

from .models import todo, tracker, todo_form, tracker_form
from .validator import todo_form_validation, tracker_form_validation

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

import logging


@login_required
def jotter(request):
	todo_list = todo.objects.all().filter(user=request.user, isCompleted=False).order_by('-added_on', 'priority')
	tracker_list = tracker.objects.all().filter(user=request.user, isCompleted=False).order_by('-added_on', 'category')

	context = {
		'todo_list': todo_list,
		'tracker_list': tracker_list
	}

	return render(request, 'jotter/jotter.html', context)


@login_required
def new_to_do(request):
	initial_form_data = {
		'priority': 'Low',
	}
	default_form = todo_form(initial=initial_form_data)
	if request.method == 'POST':
		form = todo_form(request.POST)
		return todo_form_validation(request, form)

	return render(request, 'jotter/new_todo.html', {'form': default_form})


@login_required
def new_to_track(request):
	initial_form_data = {
		'category': 'Other',
	}
	default_form = tracker_form(initial=initial_form_data)

	if request.method == 'POST':
		form = tracker_form(request.POST)
		return tracker_form_validation(request, form)

	return render(request, 'jotter/new_to_track.html', {'form': default_form})


@login_required
def edit_todo(request, item_id):
	item = todo.objects.get(pk=item_id)
	default_form = todo_form(initial={
		'title': item.title,
		'priority': item.priority,
		'notes': item.notes
	})
	if item.reminder:
		formatted_reminder = datetime.strftime(item.reminder, '%Y-%m-%dT%H:%M:%S')
		logging.info(formatted_reminder)
	else:
		formatted_reminder = False
	context = {
		'form': default_form,
		'item': item,
		'reminder': formatted_reminder
	}

	if request.method == 'POST':
		form = todo_form(request.POST, instance=item)
		return todo_form_validation(request, form)

	return render(request, 'jotter/edit_todo.html', context)


@login_required
def edit_to_track(request, item_id):
	item = tracker.objects.get(pk=item_id)
	default_form = tracker_form(initial={
		'category': item.category,
		'title': item.title,
		'chapter': item.chapter,
		'episode': item.episode,
		'link': item.link
	})
	context = {
		'category': item.category,
		'form': default_form,
		'item': item
	}

	if request.method == 'POST':
		form = tracker_form(request.POST, instance=item)
		return tracker_form_validation(request, form)

	return render(request, 'jotter/edit_to_track.html', context)


@login_required
def complete_todo(request, item_id):
	item = todo.objects.get(id=item_id)
	item.isCompleted = True
	item.completed_on = timezone.now()
	item.save()
	messages.success(request, 'Item Completed')
	return redirect('jotter')


@login_required
def complete_to_track(request, item_id):
	item = tracker.objects.get(id=item_id)
	item.isCompleted = True
	item.completed_on = timezone.now()
	item.save()
	messages.success(request, 'Item Completed')
	return redirect('jotter')

