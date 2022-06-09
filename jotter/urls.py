from django.urls import path
from . import views


urlpatterns = [
	path('', views.jotter, name='jotter'),
	path('new_reminder', views.new_to_do, name='new_to_do'),
	path('new_to_track', views.new_to_track, name='new_to_track'),
	path('completed_todo/<int:item_id>', views.complete_todo, name='complete_todo'),
	path('completed_to_track/<int:item_id>', views.complete_to_track, name='completed_to_track')
]