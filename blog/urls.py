from django.urls import path

from . import views

urlpatterns = [
    path('', views.explore, name='blog-explore'),
    path('post/<int:pk>/', views.post_detail, name='post-detail'),
    path('post/new/', views.create_post, name='post-create'),
    path('post/<int:pk>/edit/', views.edit_post, name='post-edit'),
    path('tags/', views.manage_tags, name='manage-tags'),
    path('tags/<int:tag_id>/', views.tag_posts, name='tag-posts'),
    path('author/<str:username>/', views.author_posts, name='author-posts'),
]
