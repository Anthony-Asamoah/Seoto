import logging
import json
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views import View
from django.views.decorators.http import require_http_methods

from .models import todo, tracker, todo_form, tracker_form, tracker_category_choices
from .validator import todo_form_validation, tracker_form_validation


class JotterView(View):
    @staticmethod
    @login_required
    def home(request):
        todo_qs = todo.objects.filter(
            user=request.user, isCompleted=False
        ).order_by('-added_on', 'priority')
        tracker_qs = tracker.objects.filter(
            user=request.user, isCompleted=False
        ).order_by('-added_on', 'category')
        context = {
            'todo_list': todo_qs[:3],
            'todo_extra': max(0, todo_qs.count() - 3),
            'tracker_list': tracker_qs[:3],
            'tracker_extra': max(0, tracker_qs.count() - 3),
        }
        return render(request, 'jotter/jotter.html', context)

    @staticmethod
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

    @staticmethod
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

    @staticmethod
    @login_required
    def edit_todo(request, item_id: int):
        item = todo.objects.get(pk=item_id)
        if item.reminder:
            formatted_reminder = datetime.strftime(item.reminder, '%Y-%m-%dT%H:%M:%S')
            logging.info(formatted_reminder)
        else:
            formatted_reminder = False

        if request.method == 'POST':
            force = request.POST.get('force', '0') == '1'
            client_version = request.POST.get('client_version', '')
            if client_version and not force:
                if client_version != item.updated_at.isoformat():
                    # Version conflict: re-render with user's submitted data intact
                    form = todo_form(request.POST)
                    context = {
                        'form': form,
                        'item': item,
                        'reminder': request.POST.get('reminder', ''),
                        'notes_for_editor': request.POST.get('notes', item.notes or ''),
                        'conflict': True,
                    }
                    return render(request, 'jotter/edit_todo.html', context)
            form = todo_form(request.POST, instance=item)
            return todo_form_validation(request, form)

        default_form = todo_form(initial={
            'title': item.title,
            'priority': item.priority,
            'notes': item.notes
        })
        context = {
            'form': default_form,
            'item': item,
            'reminder': formatted_reminder,
            'notes_for_editor': item.notes,
        }
        return render(request, 'jotter/edit_todo.html', context)

    @staticmethod
    @login_required
    def edit_to_track(request, item_id: int):
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

    @staticmethod
    @login_required
    def complete_todo(request, item_id):
        item = todo.objects.get(id=item_id)
        item.isCompleted = True
        item.completed_on = timezone.now()
        item.save()
        messages.success(request, 'Item Completed')
        return redirect('jotter')

    @staticmethod
    @login_required
    def complete_to_track(request, item_id):
        item = tracker.objects.get(id=item_id)
        item.isCompleted = True
        item.completed_on = timezone.now()
        item.save()
        messages.success(request, 'Item Completed')
        return redirect('jotter')

    @staticmethod
    @login_required
    def all_reminders(request):
        qs = todo.objects.filter(
            user=request.user, isCompleted=False
        ).order_by('-added_on', 'priority')

        search = request.GET.get('search', '').strip()
        priority = request.GET.get('priority', '').strip()

        if search:
            qs = qs.filter(title__icontains=search)
        if priority and priority in ['High', 'Medium', 'Low']:
            qs = qs.filter(priority=priority)

        context = {
            'todo_list': qs,
            'search': search,
            'priority': priority,
            'priority_choices': ['High', 'Medium', 'Low'],
        }
        return render(request, 'jotter/all_reminders.html', context)

    @staticmethod
    @login_required
    def all_trackers(request):
        qs = tracker.objects.filter(
            user=request.user, isCompleted=False
        ).order_by('-added_on', 'category')

        search = request.GET.get('search', '').strip()
        category = request.GET.get('category', '').strip()

        if search:
            qs = qs.filter(title__icontains=search)

        valid_categories = [c[0] for c in tracker_category_choices]
        if category and category in valid_categories:
            qs = qs.filter(category=category)

        context = {
            'tracker_list': qs,
            'search': search,
            'category': category,
            'category_choices': valid_categories,
        }
        return render(request, 'jotter/all_trackers.html', context)


@login_required
@require_http_methods(["POST"])
def create_todo_api(request):
    """API endpoint for creating todos (used by background sync)"""
    try:
        data = json.loads(request.body)

        new_todo = todo.objects.create(
            user=request.user,
            title=data.get('title'),
            priority=data.get('priority', 'Low'),
            notes=data.get('notes', '')
        )

        # Send push notification to user
        try:
            from pwa.views import send_push_notification
            send_push_notification(
                user=request.user,
                title='Todo Created',
                body=f'Your todo "{new_todo.title}" has been created',
                url='/jotter/'
            )
        except Exception as e:
            logging.warning(f'Failed to send push notification: {e}')

        return JsonResponse({
            'success': True,
            'id': new_todo.id
        })

    except Exception as e:
        logging.error(f'Failed to create todo via API: {e}')
        return JsonResponse({
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def update_todo_api(request):
    """API for background sync of todo edits. Uses client_timestamp for last-write-wins conflict resolution."""
    try:
        data = json.loads(request.body)
        item = todo.objects.get(pk=data['id'], user=request.user)

        client_ts_str = data.get('client_timestamp')
        if client_ts_str:
            client_ts = parse_datetime(client_ts_str)
            if client_ts and item.updated_at and client_ts < item.updated_at:
                return JsonResponse({
                    'success': True,
                    'saved': False,
                    'reason': 'conflict',
                    'server_timestamp': item.updated_at.isoformat()
                })

        item.title = data.get('title', item.title)
        item.priority = data.get('priority', item.priority)
        item.notes = data.get('notes', item.notes)
        reminder = data.get('reminder')
        if reminder:
            item.reminder = datetime.strptime(reminder, '%Y-%m-%dT%H:%M')
        item.save()

        return JsonResponse({
            'success': True,
            'saved': True,
            'server_timestamp': item.updated_at.isoformat()
        })

    except todo.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)
    except Exception as e:
        logging.error(f'Failed to update todo via API: {e}')
        return JsonResponse({'error': str(e)}, status=500)
