from django.urls import path

from .views import JotterView, create_todo_api, update_todo_api

urlpatterns = [
    path('', JotterView.home, name='jotter'),
    path('new_reminder', JotterView.new_to_do, name='new_to_do'),
    path('new_to_track', JotterView.new_to_track, name='new_to_track'),
    path('completed_todo/<int:item_id>', JotterView.complete_todo, name='complete_todo'),
    path('completed_to_track/<int:item_id>', JotterView.complete_to_track, name='completed_to_track'),
    path('edit_todo/<int:item_id>', JotterView.edit_todo, name='edit_todo'),
    path('edit_to_track/<int:item_id>', JotterView.edit_to_track, name='edit_to_track'),
    path('reminders/', JotterView.all_reminders, name='all_reminders'),
    path('to-watch/', JotterView.all_trackers, name='all_trackers'),
    # Background Sync API
    path('api/todo/create/', create_todo_api, name='create-todo-api'),
    path('api/todo/update/', update_todo_api, name='update-todo-api'),
]
