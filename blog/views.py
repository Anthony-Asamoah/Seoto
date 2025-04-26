import markdown
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect

from .forms import PostForm
from .models import Post, PostTags, PostReadGroup


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

    paginator = Paginator(posts, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

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

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'tag_filter': tag_filter,
        'all_tags': all_tags,
    }
    return render(request, 'blog/explore.html', context)


def post_detail(request, pk):
    post = get_object_or_404(Post, pk=pk)

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

    return render(request, 'blog/post_detail.html', {'post': post})


@login_required
def create_post(request):
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()

            # Handle M2M relationships after save
            form.save_m2m()  # This saves the tags field

            return redirect('post-detail', pk=post.pk)
    else:
        form = PostForm()

    # Get all available tags for UI
    all_tags = PostTags.objects.all()

    # Get all available read groups for UI
    if request.user.is_staff:
        all_groups = PostReadGroup.objects.all()
    else:
        all_groups = PostReadGroup.objects.filter(users=request.user)

    return render(request, 'blog/create_post.html', {
        'form': form,
        'all_tags': all_tags,
        'all_groups': all_groups
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

    # Get all available tags for UI
    all_tags = PostTags.objects.all()

    # Get all available read groups for UI
    if request.user.is_staff:
        all_groups = PostReadGroup.objects.all()
    else:
        all_groups = PostReadGroup.objects.filter(users=request.user)

    return render(request, 'blog/edit_post.html', {
        'form': form,
        'post': post,
        'all_tags': all_tags,
        'all_groups': all_groups
    })


@login_required
def manage_tags(request):
    if not request.user.is_authenticated: return HttpResponseForbidden(
        "You need to log in first"
    )

    if request.method == 'POST':
        tag_label = request.POST.get('tag_label', '').strip().capitalize()
        if tag_label:
            tag, created = PostTags.objects.get_or_create(label=tag_label)
            if created: return redirect('manage-tags')

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
    for post in posts:
        post.content_html = markdown.markdown(
            post.content,
            extensions=['extra', 'codehilite']
        )
        post.tag_list = post.tags.all()

    context = {
        'tag': tag,
        'posts': posts
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
    for post in posts:
        post.content_html = markdown.markdown(
            post.content,
            extensions=['extra', 'codehilite']
        )
        post.tag_list = post.tags.all()

    context = {
        'author': author,
        'posts': posts
    }
    return render(request, 'blog/author_posts.html', context)
