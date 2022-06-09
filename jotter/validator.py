import logging
from datetime import datetime

from django.contrib import messages
from django.shortcuts import redirect, HttpResponseRedirect


def todo_form_validation(request, form):
	reminder = request.POST['reminder']
	if form.is_valid():
		item = form.save(commit=False)
		item.user = request.user
		if reminder:
			reminder_formatted = datetime.strptime(reminder, '%Y-%m-%dT%H:%M')
			if reminder_formatted < datetime.now():
				messages.error(request, 'reminder cannot be set to the past.')
				return redirect('new_to_do')
			item.reminder = reminder_formatted
		try:
			item.save()
			messages.success(request, 'Item added.')
			return redirect('jotter')
		except Exception as e:
			logging.error(e)

	messages.error(request, 'Failed to Submit')
	return False


def tracker_form_validation(request, form):
	if form.is_valid():
		item = form.save(commit=False)
		item.user = request.user
		try:
			item.save()
			messages.success(request, 'Item added.')
			return redirect('jotter')
		except Exception as e:
			logging.error(e)

	messages.error(request, 'Failed to Submit')
	return False
