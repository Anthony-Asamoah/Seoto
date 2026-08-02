import logging
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db.models import Q
from django.http import Http404, HttpResponseForbidden, HttpResponseRedirect, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_http_methods

from utils.paginator import apply_pagination
from .forms import PostForm
from .models import Post, PostTags, PostReadGroup, PostComment
from .utils import (
    trigger_author_comment_notification,
    notify_user_added_to_group,
    notify_user_removed_from_group,
    notify_owner_user_left_group,
    pluralize_label,
)

RESULTS_PER_PAGE = 5


def explore(request):
    if request.user.is_authenticated:
        # Get posts that are:
        # 1. Public, OR
        # 2. User is the author, OR
        # 3. User is in an allowed group, OR
        # 4. User is directly allowed
        base_queryset = Post.objects.filter(
            Q(is_public=True) |
            Q(author=request.user) |
            Q(allowed_groups__users=request.user) |
            Q(allowed_users=request.user)
        ).distinct()
    else:
        # Only show public posts to unauthenticated users
        base_queryset = Post.objects.filter(is_public=True)

    search_query = request.GET.get('search', '')
    tag_filter = request.GET.get('tag', '')

    if search_query:
        posts = base_queryset.filter(
            Q(title__icontains=search_query) |
            Q(author__username__icontains=search_query)
        )
    else:
        posts = base_queryset

    if tag_filter: posts = posts.filter(tags__label=tag_filter)

    posts = posts.order_by('-date_posted')
    page_obj = apply_pagination(posts, request.GET.get('page'), RESULTS_PER_PAGE)

    for post in page_obj:
        post.tag_list = post.tags.all()

    # Get all tags for the filter dropdown
    all_tags = PostTags.objects.all()

    # Get popular tags
    popular_tags = PostTags.objects.all().order_by('-hits')[:5]

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'tag_filter': tag_filter,
        'all_tags': all_tags,
        'popular_tags': popular_tags
    }
    return render(request, 'blog/explore.html', context)


def post_detail(request, pk):
    post = get_object_or_404(Post.objects.prefetch_related('comments'), pk=pk)

    # Check if the user has access to this post
    if not post.is_public:
        if not request.user.is_authenticated:
            return HttpResponseForbidden("You need to log in to view this post.")

        # Check if user has access
        has_access = (
                request.user == post.author or
                post.allowed_users.filter(id=request.user.id).exists() or
                post.allowed_groups.filter(users=request.user).exists()
        )

        if not has_access:
            return HttpResponseForbidden("You don't have permission to view this post.")
    # Get tags for display
    post.tag_list = post.tags.all()

    # Get comment visibility info
    visible_comments = post.comments.filter(is_visible=True)
    has_visible_comments = visible_comments.exists()

    PostTags.increment_hits(ids=list(post.tag_list.values_list('id', flat=True)))
    return render(request, 'blog/post_detail.html', {
        'post': post,
        'visible_comments': visible_comments,
        'has_visible_comments': has_visible_comments
    })


@login_required
def comment_privately(request, pk):
    if request.method == 'POST':
        post = get_object_or_404(Post, pk=pk)
        comment = request.POST.get('comment', '').strip()
        if comment:
            comment = post.comments.create(author=request.user, content=comment)
            trigger_author_comment_notification(comment, post)
            messages.success(request, 'The author has been notified of your comment.')

    return redirect('post-detail', pk=pk)


@login_required
def delete_comment(request, post_pk, comment_pk):
    if request.method == 'GET':
        comment = get_object_or_404(PostComment, pk=comment_pk)
        if not request.user == comment.author: return HttpResponseForbidden(
            "You don't have permission to delete this comment."
        )
        comment.delete()
    return redirect('post-detail', pk=post_pk)


@login_required
def toggle_comment_visibility(request, post_pk, comment_pk):
    """Toggle visibility of a specific comment (only for post author)"""
    comment = get_object_or_404(PostComment, pk=comment_pk, post_id=post_pk)
    post = comment.post

    # Only post author can toggle comment visibility
    if request.user != post.author:
        return HttpResponseForbidden("You don't have permission to toggle comment visibility.")

    if request.method == 'POST':
        # Toggle the comment's visibility
        comment.is_visible = not comment.is_visible
        comment.save()

        if comment.is_visible:
            messages.success(request, 'Comment is now visible to readers.')
        else:
            messages.success(request, 'Comment is now hidden from readers.')

    return redirect('post-detail', pk=post_pk)


@login_required
def create_post(request):
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()

            # Tags are now handled in the form's save method
            form.save(commit=True)

            return redirect('post-detail', pk=post.pk)
    else:
        form = PostForm()

    return render(request, 'blog/create_post.html', {
        'form': form
    })


@login_required
def edit_post(request, pk):
    post = get_object_or_404(Post, pk=pk)

    # Only author can edit post
    if post.author != request.user and not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to edit this post.")

    if request.method == 'POST':
        form = PostForm(request.POST, instance=post)
        if form.is_valid():
            form.save()
            return redirect('post-detail', pk=post.pk)
    else:
        form = PostForm(instance=post)

    return render(request, 'blog/edit_post.html', {
        'form': form,
        'post': post
    })


@login_required
@require_http_methods(["POST"])
def delete_post(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if post.author != request.user and not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to delete this post.")
    post.delete()
    messages.success(request, 'Post deleted successfully.')
    return redirect('blog-explore')


@login_required
def manage_tags(request):
    if not request.user.is_authenticated: return HttpResponseForbidden(
        "You need to log in first"
    )

    if request.method == 'POST':
        tag_label = request.POST.get('tag_label', '').strip().lower()
        if tag_label:
            tag, created = PostTags.objects.get_or_create(label=tag_label)
            if created:
                messages.success(request, f'Tag "{tag_label}" created successfully.')
            else:
                messages.info(request, f'Tag "{tag_label}" already exists.')
            return redirect('manage-tags')

    tags = PostTags.objects.all().order_by('label')
    return render(request, 'blog/manage_tags.html', {'tags': tags})


@login_required
def tag_posts(request, tag_id):
    tag = get_object_or_404(PostTags, id=tag_id)

    if request.user.is_authenticated:
        posts = Post.objects.filter(
            tags=tag
        ).filter(
            Q(is_public=True) |
            Q(author=request.user) |
            Q(allowed_groups__users=request.user) |
            Q(allowed_users=request.user)
        ).distinct().order_by('-date_posted')
    else:
        posts = Post.objects.filter(tags=tag, is_public=True).order_by('-date_posted')

    page_obj = apply_pagination(posts, request.GET.get('page'), RESULTS_PER_PAGE)

    tag.increment_hits(ids=[tag.id])

    for post in page_obj:
        post.tag_list = post.tags.all()

    context = {
        'tag': tag,
        'page_obj': page_obj
    }
    return render(request, 'blog/tag_posts.html', context)


@login_required
def author_posts(request, username):
    author = get_object_or_404(User, username=username)

    if request.user.is_authenticated:
        posts = Post.objects.filter(
            author=author
        ).filter(
            Q(is_public=True) |
            Q(author=request.user) |
            Q(allowed_groups__users=request.user) |
            Q(allowed_users=request.user)
        ).distinct().order_by('-date_posted')
    else:
        posts = Post.objects.filter(author=author, is_public=True).order_by('-date_posted')

    page_obj = apply_pagination(posts, request.GET.get('page'), RESULTS_PER_PAGE)
    for post in page_obj:
        post.tag_list = post.tags.all()

    context = {
        'author': author,
        'page_obj': page_obj
    }
    return render(request, 'blog/author_posts.html', context)


@login_required
def manage_read_groups(request):
    """Manage read groups - list and create"""
    if request.method == 'POST':
        group_label = pluralize_label(request.POST.get('group_label', '').strip())
        if group_label:
            # Check if user already has a group with this name
            existing = PostReadGroup.objects.filter(author=request.user, label=group_label).exists()
            if not existing:
                group = PostReadGroup.objects.create(label=group_label, author=request.user)
                messages.success(request, f'Read group "{group_label}" created successfully. Add members below.')
                return redirect('edit-read-group', group_id=group.id)
            else:
                messages.warning(request, f'You already have a read group named "{group_label}".')
                return redirect('manage-read-groups')

    # Get user's read groups
    groups = PostReadGroup.objects.filter(author=request.user).order_by('label')
    return render(request, 'blog/manage_read_groups.html', {'groups': groups})


@login_required
def edit_read_group(request, group_id):
    """Edit a specific read group - manage members"""
    group = get_object_or_404(PostReadGroup, id=group_id, author=request.user)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_user':
            username = request.POST.get('username', '').strip()
            if username:
                try:
                    # Case-insensitive username lookup
                    user = User.objects.get(username__iexact=username)
                    if user not in group.users.all():
                        group.users.add(user)
                        messages.success(request, f'User "@{user.username}" added to group.')
                        # Send notification to the added user
                        try:
                            notify_user_added_to_group(user, group)
                        except:
                            logging.warning(f'Failed to send notification to {user.username}')
                    else:
                        messages.warning(request, f'User "@{user.username}" is already in this group.')
                except User.DoesNotExist:
                    messages.error(request, f'User "{username}" does not exist.')

        elif action == 'remove_user':
            user_id = request.POST.get('user_id')
            if user_id:
                user = get_object_or_404(User, id=user_id)
                group.users.remove(user)
                messages.success(request, f'User "{user.username}" removed from group.')
                # Send notification to the removed user
                try:
                    notify_user_removed_from_group(user, group)
                except:
                    logging.warning(f'Failed to send notification to {user.username}')

        elif action == 'rename':
            new_label = pluralize_label(request.POST.get('group_label', '').strip())
            if new_label and new_label != group.label:
                # Check if user already has another group with this name
                existing = PostReadGroup.objects.filter(
                    author=request.user,
                    label=new_label
                ).exclude(id=group.id).exists()

                if not existing:
                    group.label = new_label
                    group.save()
                    messages.success(request, f'Group renamed to "{new_label}".')
                else:
                    messages.warning(request, f'You already have a read group named "{new_label}".')

        return redirect('edit-read-group', group_id=group.id)

    context = {
        'group': group,
        'all_users': User.objects.exclude(id=request.user.id).order_by('username')
    }
    return render(request, 'blog/edit_read_group.html', context)


@login_required
def delete_read_group(request, group_id):
    """Delete a read group"""
    group = get_object_or_404(PostReadGroup, id=group_id, author=request.user)

    if request.method == 'POST':
        group_label = group.label
        group.delete()
        messages.success(request, f'Read group "{group_label}" deleted successfully.')
        return redirect('manage-read-groups')

    return render(request, 'blog/delete_read_group.html', {'group': group})


@login_required
def my_read_groups(request):
    """View groups that the user is a member of (not owner)"""
    # Get groups where the user is a member (but not the author)
    groups = PostReadGroup.objects.filter(users=request.user).exclude(author=request.user).order_by('label')

    # Annotate each group with post count
    for group in groups:
        group.post_count = group.allowed_posts.count()

    return render(request, 'blog/my_read_groups.html', {'groups': groups})


@login_required
def leave_read_group(request, group_id):
    """Leave a read group"""
    group = get_object_or_404(PostReadGroup, id=group_id)

    # Check if user is actually in this group
    if request.user not in group.users.all():
        messages.error(request, 'You are not a member of this group.')
        return redirect('my-read-groups')

    # Prevent owner from leaving their own group
    if group.author == request.user:
        messages.error(request, 'You cannot leave a group you own. Delete it instead.')
        return redirect('manage-read-groups')

    if request.method == 'POST':
        group_label = group.label
        group_owner = group.author
        group.users.remove(request.user)
        messages.success(request, f'You have left the group "{group_label}".')

        # Notify group owner
        try:
            notify_owner_user_left_group(request.user, group)
        except:
            logging.warning(f'Failed to notify {group_owner.username} about {request.user.username} leaving')

        return redirect('my-read-groups')

    return render(request, 'blog/leave_read_group.html', {'group': group})


@login_required
@require_http_methods(["POST"])
def create_post_api(request):
    """API endpoint for creating posts (used by background sync)"""
    try:
        data = json.loads(request.body)

        post = Post.objects.create(
            author=request.user,
            title=data.get('title'),
            content=data.get('content'),
            is_public=data.get('is_public', False)
        )

        # Send push notification to user
        try:
            from domains.pwa.services import send_push_notification
            send_push_notification(
                user=request.user,
                title='Post Published',
                body=f'Your post "{post.title}" has been published',
                url=f'/blog/post/{post.id}/'
            )
        except Exception as e:
            logging.warning(f'Failed to send push notification: {e}')

        return JsonResponse({
            'success': True,
            'id': post.id
        })

    except Exception as e:
        logging.error(f'Failed to create post via API: {e}')
        return JsonResponse({
            'error': str(e)
        }, status=500)


def serve_blog_media(request, path):
    """Proxy view that generates a fresh signed URL and redirects.

    Storing proxy URLs (instead of pre-signed S3 URLs) in post content means
    the embedded URLs never expire — a fresh signed URL is produced on every access.
    """
    if not (path.startswith('blog/images/') or path.startswith('blog/media/')):
        raise Http404
    if not default_storage.exists(path):
        raise Http404
    return HttpResponseRedirect(default_storage.url(path))


@login_required
@require_http_methods(["POST"])
def upload_media(request):
    """Handle media uploads (image, video, audio, document) from the blog editor."""
    from django.conf import settings as django_settings

    file = request.FILES.get('file')
    if not file:
        return JsonResponse({'error': 'No file provided'}, status=400)

    content_type = file.content_type or ''

    if content_type.startswith('video/'):
        max_mb = django_settings.BLOG_VIDEO_MAX_SIZE_MB
    else:
        max_mb = django_settings.BLOG_UPLOAD_MAX_SIZE_MB

    if file.size > max_mb * 1024 * 1024:
        return JsonResponse({'error': f'File exceeds the {max_mb} MB limit.'}, status=400)

    # Validate images with Pillow
    if content_type.startswith('image/'):
        try:
            from PIL import Image as PILImage
            img = PILImage.open(file)
            img.verify()
            file.seek(0)
        except Exception:
            return JsonResponse({'error': 'Invalid image file.'}, status=400)

    filename = f'blog/media/{request.user.id}_{file.name}'
    path = default_storage.save(filename, ContentFile(file.read()))

    # On AWS, store a proxy URL so the signed URL never expires in saved content.
    # On local storage, use the direct media URL (no signing, no expiry).
    if django_settings.MEDIA_STORAGE == 'AWS':
        from django.urls import reverse
        url = reverse('blog-serve-media', kwargs={'path': path})
    else:
        url = default_storage.url(path)

    if content_type.startswith('image/'):
        html = f'<img src="{url}" style="max-width:100%;">'
    elif content_type.startswith('video/'):
        html = (
            f'<video controls preload="metadata" style="width:100%;">'
            f'<source src="{url}" type="{content_type}"></video>'
        )
    elif content_type.startswith('audio/'):
        html = (
            f'<audio controls preload="none" style="width:100%;">'
            f'<source src="{url}" type="{content_type}"></audio>'
        )
    elif content_type == 'application/pdf':
        html = (
            f'<div class="blog-doc-embed">'
            f'<iframe src="{url}" width="100%" height="500" style="border:none;"></iframe>'
            f'<a href="{url}" target="_blank" download>Download PDF</a>'
            f'</div>'
        )
    else:
        html = (
            f'<div class="blog-doc-embed">'
            f'<a href="{url}" target="_blank" download class="btn btn-outline-secondary">'
            f'<i class="fas fa-file"></i> Download: {file.name}</a>'
            f'</div>'
        )

    return JsonResponse({'url': url, 'html': html})


@login_required
@require_http_methods(["POST"])
def upload_image(request):
    """Handle image uploads from the rich text editor"""
    image = request.FILES.get('image')
    if not image:
        return JsonResponse({'error': 'No image provided'}, status=400)

    # Validate it's a real image using Pillow
    try:
        from PIL import Image as PILImage
        img = PILImage.open(image)
        img.verify()
        image.seek(0)
    except Exception:
        return JsonResponse({'error': 'Invalid image file'}, status=400)

    filename = f'blog/images/{request.user.id}_{image.name}'
    path = default_storage.save(filename, ContentFile(image.read()))
    url = default_storage.url(path)

    return JsonResponse({'url': url})
