import markdown
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect

from utils.paginator import apply_pagination
from .forms import PostForm
from .models import Post, PostTags, PostReadGroup, PostComment
from .utils import trigger_author_comment_notification

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

    # Convert markdown to HTML for post previews
    for post in page_obj:
        post.content_html = markdown.markdown(
            post.content,
            extensions=['extra', 'codehilite']
        )
        # Get tags for display
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
    # Convert markdown to HTML
    post.content_html = markdown.markdown(
        post.content,
        extensions=['extra', 'codehilite']
    )

    # Get tags for display
    post.tag_list = post.tags.all()

    PostTags.increment_hits(ids=list(post.tag_list.values_list('id', flat=True)))
    return render(request, 'blog/post_detail.html', {'post': post})


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

    # Convert markdown to HTML for post previews
    page_obj = apply_pagination(posts, request.GET.get('page'), RESULTS_PER_PAGE)

    tag.increment_hits(ids=[tag.id])

    for post in page_obj:
        post.content_html = markdown.markdown(
            post.content,
            extensions=['extra', 'codehilite']
        )
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

    # Convert markdown to HTML for post previews
    page_obj = apply_pagination(posts, request.GET.get('page'), RESULTS_PER_PAGE)
    for post in page_obj:
        post.content_html = markdown.markdown(
            post.content,
            extensions=['extra', 'codehilite']
        )
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
        group_label = request.POST.get('group_label', '').strip()
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

        elif action == 'rename':
            new_label = request.POST.get('group_label', '').strip()
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
