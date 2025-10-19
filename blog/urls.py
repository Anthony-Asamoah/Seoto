from django.urls import path

from . import views

urlpatterns = [
    path('', views.explore, name='blog-explore'),
    path('post/<int:pk>/', views.post_detail, name='post-detail'),
    path('post/<int:pk>/comment/', views.comment_privately, name='comment-privately'),
    path('post/<int:post_pk>/comment/<int:comment_pk>/', views.delete_comment, name='delete-comment'),
    path('post/new/', views.create_post, name='post-create'),
    path('post/<int:pk>/edit/', views.edit_post, name='post-edit'),
    path('tags/', views.manage_tags, name='manage-tags'),
    path('tags/<int:tag_id>/', views.tag_posts, name='tag-posts'),
    path('author/<str:username>/', views.author_posts, name='author-posts'),
    path('read-groups/', views.manage_read_groups, name='manage-read-groups'),
    path('read-groups/my/', views.my_read_groups, name='my-read-groups'),
    path('read-groups/<int:group_id>/edit/', views.edit_read_group, name='edit-read-group'),
    path('read-groups/<int:group_id>/delete/', views.delete_read_group, name='delete-read-group'),
    path('read-groups/<int:group_id>/leave/', views.leave_read_group, name='leave-read-group'),
]
