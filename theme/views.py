from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404

from .forms import CustomizeThemeForm, PublishThemeForm, PresetForm, RatingForm
from .models import ThemePreset, ThemeRating
from .utils import send_theme_notification, get_or_create_user_theme


def is_staff(user):
    """Check if user is staff/admin"""
    return user.is_staff


# ==================== Public Views ====================

@login_required
def theme_home(request):
    """
    Main theme dashboard showing current theme and quick access to features.
    """
    user_theme = get_or_create_user_theme(request.user)

    # Get featured and popular themes
    featured_themes = ThemePreset.objects.filter(
        Q(is_official=True) | Q(is_public=True, is_public_verified=True),
        is_featured=True
    )[:3]

    popular_themes = ThemePreset.objects.filter(
        Q(is_official=True) | Q(is_public=True, is_public_verified=True)
    ).exclude(id__in=featured_themes.values_list('id', flat=True)).order_by('-rating_count')[:3]

    context = {
        'user_theme': user_theme,
        'current_colors': user_theme.get_colors(),
        'featured_themes': featured_themes,
        'popular_themes': popular_themes,
    }

    return render(request, 'theme/theme_home.html', context)


def preset_list(request):
    """
    Browse all available theme presets (official and verified public).
    """
    # Get filter from query params
    filter_type = request.GET.get('filter', 'all')

    # Base query: official or verified public themes
    themes = ThemePreset.objects.filter(
        Q(is_official=True) | Q(is_public=True, is_public_verified=True)
    )

    # Apply filters
    if filter_type == 'official':
        themes = themes.filter(is_official=True)
    elif filter_type == 'community':
        themes = themes.filter(is_official=False, is_public=True, is_public_verified=True)
    elif filter_type == 'featured':
        themes = themes.filter(is_featured=True)

    context = {
        'themes': themes,
        'filter_type': filter_type,
    }

    return render(request, 'theme/preset_list.html', context)


def preset_detail(request, preset_id):
    """
    View details of a specific theme preset with preview.
    """
    theme = get_object_or_404(ThemePreset, id=preset_id)

    # Check if theme is available (official or verified public)
    if not theme.is_available:
        messages.error(request, 'This theme is not available.')
        return redirect('theme:preset_list')

    # Get user's rating if logged in
    user_rating = None
    if request.user.is_authenticated:
        user_rating = ThemeRating.objects.filter(user=request.user, theme=theme).first()

    context = {
        'theme': theme,
        'user_rating': user_rating,
        'colors': {
            'primary_color': theme.primary_color,
            'secondary_color': theme.secondary_color,
            'background_color': theme.background_color,
            'text_color': theme.text_color,
            'navbar_bg': theme.navbar_bg,
            'navbar_text': theme.navbar_text,
        }
    }

    return render(request, 'theme/preset_detail.html', context)


@login_required
def apply_preset(request, preset_id):
    """
    Apply a theme preset to the user's account.
    """
    theme = get_object_or_404(ThemePreset, id=preset_id)

    if not theme.is_available:
        messages.error(request, 'This theme is not available.')
        return redirect('theme:preset_list')

    # Get or create user theme
    user_theme = get_or_create_user_theme(request.user)

    # Apply preset
    user_theme.active_preset = theme
    user_theme.is_using_preset = True
    user_theme.save()

    messages.success(request, f'Theme "{theme.name}" applied successfully!')
    return redirect('theme:theme_home')


@login_required
def customize_theme(request):
    """
    Allow user to customize their own theme colors.
    """
    user_theme = get_or_create_user_theme(request.user)

    if request.method == 'POST':
        form = CustomizeThemeForm(request.POST, instance=user_theme)
        if form.is_valid():
            user_theme = form.save(commit=False)
            user_theme.is_using_preset = False
            user_theme.save()
            messages.success(request, 'Your custom theme has been saved!')
            return redirect('theme:theme_home')
    else:
        # Pre-populate form with current colors
        colors = user_theme.get_colors()
        initial_data = {
            'custom_primary_color': colors['primary_color'],
            'custom_secondary_color': colors['secondary_color'],
            'custom_background_color': colors['background_color'],
            'custom_text_color': colors['text_color'],
            'custom_text_head_color': colors['text_head_color'],
            'custom_navbar_bg': colors['navbar_bg'],
            'custom_navbar_text': colors['navbar_text'],
            'custom_btn_success_bg': colors['btn_success_bg'],
            'custom_btn_success_text': colors['btn_success_text'],
            'custom_btn_danger_bg': colors['btn_danger_bg'],
            'custom_btn_danger_text': colors['btn_danger_text'],
            'custom_btn_warning_bg': colors['btn_warning_bg'],
            'custom_btn_warning_text': colors['btn_warning_text'],
            'custom_btn_info_bg': colors['btn_info_bg'],
            'custom_btn_info_text': colors['btn_info_text'],
            'custom_card_bg_color': colors['card_bg_color'],
            'custom_card_header_bg_color': colors['card_header_bg_color'],
            'custom_card_text_color': colors['card_text_color'],
        }
        form = CustomizeThemeForm(instance=user_theme, initial=initial_data)

    context = {
        'form': form,
        'user_theme': user_theme,
        'current_colors': user_theme.get_colors(),
    }

    return render(request, 'theme/customize.html', context)


@login_required
def publish_theme(request):
    """
    Publish user's custom theme for public use (requires admin verification).
    """
    user_theme = get_or_create_user_theme(request.user)

    # Check if user has custom theme
    if user_theme.is_using_preset:
        messages.warning(request,
                         'You need to create a custom theme before publishing. Visit the customize page first.')
        return redirect('theme:customize')

    if request.method == 'POST':
        form = PublishThemeForm(request.POST, user=request.user)
        if form.is_valid():
            # Create new ThemePreset from user's custom colors
            theme = ThemePreset.objects.create(
                name=form.cleaned_data['name'],
                description=form.cleaned_data['description'],
                created_by=request.user,
                primary_color=user_theme.custom_primary_color or '#007bff',
                secondary_color=user_theme.custom_secondary_color or '#6c757d',
                background_color=user_theme.custom_background_color or '#ffffff',
                text_color=user_theme.custom_text_color or '#212529',
                text_head_color=user_theme.custom_text_head_color or '#000000',
                navbar_bg=user_theme.custom_navbar_bg or '#f8f9fa',
                navbar_text=user_theme.custom_navbar_text or '#000000',
                btn_success_bg=user_theme.custom_btn_success_bg or '#28a745',
                btn_success_text=user_theme.custom_btn_success_text or '#ffffff',
                btn_danger_bg=user_theme.custom_btn_danger_bg or '#dc3545',
                btn_danger_text=user_theme.custom_btn_danger_text or '#ffffff',
                btn_warning_bg=user_theme.custom_btn_warning_bg or '#ffc107',
                btn_warning_text=user_theme.custom_btn_warning_text or '#000000',
                btn_info_bg=user_theme.custom_btn_info_bg or '#17a2b8',
                btn_info_text=user_theme.custom_btn_info_text or '#ffffff',
                card_bg_color=user_theme.custom_card_bg_color or '#ffffff',
                card_header_bg_color=user_theme.custom_card_header_bg_color or '#f8f9fa',
                card_text_color=user_theme.custom_card_text_color or '#212529',
                is_public=True,
                is_public_verified=False,
                is_official=False
            )

            # Send notification to admins
            send_theme_notification(theme, 'submitted')

            messages.success(request,
                             'Your theme has been submitted for review! You will be notified once it is verified.')
            return redirect('theme:theme_home')
    else:
        form = PublishThemeForm(user=request.user)

    context = {
        'form': form,
        'current_colors': user_theme.get_colors(),
    }

    return render(request, 'theme/publish_form.html', context)


@login_required
def rate_theme(request, preset_id):
    """
    Rate a theme preset (1-5 stars).
    """
    theme = get_object_or_404(ThemePreset, id=preset_id)

    if not theme.is_available:
        messages.error(request, 'This theme is not available for rating.')
        return redirect('theme:preset_list')

    if request.method == 'POST':
        # Check if user already rated
        existing_rating = ThemeRating.objects.filter(user=request.user, theme=theme).first()

        if existing_rating:
            # Update existing rating
            form = RatingForm(request.POST, instance=existing_rating, user=request.user, theme=theme)
        else:
            # Create new rating
            form = RatingForm(request.POST, user=request.user, theme=theme)

        if form.is_valid():
            form.save()
            messages.success(request, f'Your rating for "{theme.name}" has been saved!')
            return redirect('theme:preset_detail', preset_id=preset_id)

    return redirect('theme:preset_detail', preset_id=preset_id)


# ==================== Admin Views ====================

@login_required
@user_passes_test(is_staff)
def admin_create_preset(request):
    """
    Admin view to create official theme presets.
    """
    if request.method == 'POST':
        form = PresetForm(request.POST)
        if form.is_valid():
            theme = form.save(commit=False)
            theme.created_by = request.user
            theme.save()
            messages.success(request, f'Official theme "{theme.name}" created successfully!')
            return redirect('theme:theme_home')
    else:
        form = PresetForm()

    context = {
        'form': form,
    }

    return render(request, 'theme/admin_create.html', context)


@login_required
@user_passes_test(is_staff)
def admin_verify_queue(request):
    """
    Admin view to see and verify pending public themes.
    """
    pending_themes = ThemePreset.objects.filter(
        is_public=True,
        is_public_verified=False
    ).order_by('-created_at')

    context = {
        'pending_themes': pending_themes,
    }

    return render(request, 'theme/admin_verify.html', context)


@login_required
@user_passes_test(is_staff)
def admin_verify_theme(request, preset_id):
    """
    Admin approves a theme for public use.
    """
    theme = get_object_or_404(ThemePreset, id=preset_id)

    theme.is_public_verified = True
    theme.save()

    # Send notification to user
    send_theme_notification(theme, 'verified')

    messages.success(request, f'Theme "{theme.name}" has been verified and is now public!')
    return redirect('theme:admin_verify_queue')


@login_required
@user_passes_test(is_staff)
def admin_reject_theme(request, preset_id):
    """
    Admin rejects a theme submission.
    """
    theme = get_object_or_404(ThemePreset, id=preset_id)

    # Send notification to user
    send_theme_notification(theme, 'rejected')

    # Delete the theme
    theme_name = theme.name
    theme.delete()

    messages.info(request, f'Theme "{theme_name}" has been rejected and removed.')
    return redirect('theme:admin_verify_queue')


@login_required
@user_passes_test(is_staff)
def admin_toggle_featured(request, preset_id):
    """
    Admin toggles featured status of a theme.
    """
    theme = get_object_or_404(ThemePreset, id=preset_id)

    theme.is_featured = not theme.is_featured
    theme.save()

    status = 'featured' if theme.is_featured else 'unfeatured'
    messages.success(request, f'Theme "{theme.name}" has been {status}!')

    return redirect(request.META.get('HTTP_REFERER', 'theme:theme_home'))
