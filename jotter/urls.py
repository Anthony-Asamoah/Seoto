from django.urls import path

from .views import JotterView

urlpatterns = [
    path('', JotterView.home, name='jotter'),
    path('new_reminder', JotterView.new_to_do, name='new_to_do'),
    path('new_to_track', JotterView.new_to_track, name='new_to_track'),
    path('completed_todo/<int:item_id>', JotterView.complete_todo, name='complete_todo'),
    path('completed_to_track/<int:item_id>', JotterView.complete_to_track, name='completed_to_track'),
    path('edit_todo/<int:item_id>', JotterView.edit_todo, name='edit_todo'),
    path('edit_to_track/<int:item_id>', JotterView.edit_to_track, name='edit_to_track'),
]
