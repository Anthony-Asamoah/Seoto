from django.contrib import messages
from django.contrib.auth.decorators import permission_required, login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods

from . import services
from .forms import UserMealForm
from .models import meal, userPreference, MealTimeSlot, UserMealSchedule
from .serializer import serialize_mealtime, serialize_all
from utils.paginator import apply_pagination


def foodie(request):
    context = services.suggest(request.user)
    return render(request, 'foodie/foodie.html', context)


@login_required
def foodie_config(request, mealtime=None):
    slots = MealTimeSlot.objects.all()

    if mealtime is None:
        return render(request, 'foodie/foodie_config.html', {
            'mealtime': None,
            'slots': slots,
            'meals': [],
        })

    slot = get_object_or_404(MealTimeSlot, pk=mealtime)

    if request.method == 'POST':
        action = request.POST.get('action', '')
        meal_id = request.POST.get('meal_id')
        redirect_url = f'/foodie/config/{mealtime}'
        qs = request.POST.get('redirect_qs', '')
        if qs:
            redirect_url += f'?{qs}'

        if action == 'add' and meal_id:
            m = get_object_or_404(meal, pk=meal_id)
            userPreference.objects.get_or_create(
                user=request.user, meal=m, slot=slot,
                defaults={'isAvailable': True}
            )
        elif action == 'remove' and meal_id:
            userPreference.objects.filter(user=request.user, meal_id=meal_id, slot=slot).delete()

        return redirect(redirect_url)

    search_query = request.GET.get('search', '').strip()
    category_filter = request.GET.get('category', '').strip()

    selected_ids = list(
        userPreference.objects.filter(user=request.user, slot=slot).values_list('meal_id', flat=True)
    )
    selected_meal_objects = meal.objects.filter(id__in=selected_ids).order_by('name')

    available_qs = meal.objects.filter(
        Q(created_by=None) | Q(created_by=request.user) | Q(is_public=True)
    ).exclude(id__in=selected_ids).order_by('name')
    if search_query:
        available_qs = available_qs.filter(name__icontains=search_query)
    if category_filter:
        available_qs = available_qs.filter(categories__icontains=f'"{category_filter}"')

    all_categories = sorted({
        cat
        for cats in meal.objects.exclude(categories=[]).values_list('categories', flat=True)
        for cat in (cats or [])
    })

    page_obj = apply_pagination(available_qs, request.GET.get('page'), 13)

    query_params = {}
    if search_query:
        query_params['search'] = search_query
    if category_filter:
        query_params['category'] = category_filter

    context = {
        'mealtime': mealtime,
        'mealtime_readable': slot.label.capitalize(),
        'slot': slot,
        'slots': slots,
        'meals': page_obj,
        'selected_meal_objects': selected_meal_objects,
        'search_query': search_query,
        'category_filter': category_filter,
        'all_categories': all_categories,
        'query_params': query_params,
    }
    return render(request, 'foodie/foodie_config.html', context)


# User meal management

@login_required
def my_meals(request):
    user_meals = meal.objects.filter(created_by=request.user).order_by('name')
    return render(request, 'foodie/my_meals.html', {'user_meals': user_meals})


@login_required
def meal_create(request):
    if request.method == 'POST':
        form = UserMealForm(request.POST, request.FILES)
        if form.is_valid():
            new_meal = form.save(commit=False)
            new_meal.created_by = request.user
            new_meal.save()
            messages.success(request, f'"{new_meal.name}" added to your foods.')
            return redirect('foodie_my_meals')
    else:
        form = UserMealForm()
    return render(request, 'foodie/meal_form.html', {'form': form, 'is_edit': False})


@login_required
def meal_edit(request, pk):
    m = get_object_or_404(meal, pk=pk, created_by=request.user)
    slots = MealTimeSlot.objects.all()

    if request.method == 'POST':
        form = UserMealForm(request.POST, request.FILES, instance=m)
        if form.is_valid():
            form.save()
            selected_labels = request.POST.getlist('mealtimes')
            # Remove deselected slots, add selected ones
            userPreference.objects.filter(user=request.user, meal=m).exclude(slot_id__in=selected_labels).delete()
            for label in selected_labels:
                slot = MealTimeSlot.objects.filter(pk=label).first()
                if slot:
                    userPreference.objects.get_or_create(
                        user=request.user, meal=m, slot=slot,
                        defaults={'isAvailable': True}
                    )
            messages.success(request, f'"{m.name}" updated.')
            return redirect('foodie_my_meals')
    else:
        form = UserMealForm(instance=m)

    active_mealtimes = list(
        userPreference.objects.filter(user=request.user, meal=m).values_list('slot_id', flat=True)
    )
    return render(request, 'foodie/meal_form.html', {
        'form': form,
        'is_edit': True,
        'meal_obj': m,
        'slots': slots,
        'active_mealtimes': active_mealtimes,
    })


@login_required
@require_http_methods(["POST"])
def meal_delete(request, pk):
    m = get_object_or_404(meal, pk=pk, created_by=request.user)
    name = m.name
    if m.main_img:
        m.main_img.delete(save=False)
    m.delete()
    messages.success(request, f'"{name}" deleted.')
    return redirect('foodie_my_meals')


@login_required
def meal_schedule(request):
    """Let users view, edit, add, and remove their personal meal time schedule entries."""
    from datetime import time as dt_time

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add':
            slot_label = request.POST.get('slot_label', '').strip().lower()
            raw_time = request.POST.get('time', '').strip()
            if not slot_label:
                messages.error(request, 'Please enter a slot name.')
            elif slot_label == 'fancy':
                messages.error(request, '"Fancy" is a reserved slot.')
            elif not raw_time:
                messages.error(request, 'Please enter a time.')
            else:
                try:
                    h, m = raw_time.split(':')
                    slot, _ = MealTimeSlot.objects.get_or_create(
                        label=slot_label,
                        defaults={'default_time': dt_time(int(h), int(m))}
                    )
                    _, created = UserMealSchedule.objects.get_or_create(
                        user=request.user, slot=slot,
                        defaults={'time': dt_time(int(h), int(m))}
                    )
                    if created:
                        messages.success(request, f'{slot.label.capitalize()} added to your schedule.')
                    else:
                        messages.info(request, f'{slot.label.capitalize()} is already in your schedule.')
                except ValueError:
                    messages.error(request, f'Invalid time: "{raw_time}"')

        elif action == 'remove':
            schedule_id = request.POST.get('schedule_id')
            UserMealSchedule.objects.filter(pk=schedule_id, user=request.user).delete()
            messages.success(request, 'Slot removed from your schedule.')

        elif action == 'save':
            schedules = UserMealSchedule.objects.filter(user=request.user)
            errors = []
            for schedule in schedules:
                raw = request.POST.get(f'time_{schedule.slot.label}', '').strip()
                if raw:
                    try:
                        h, m = raw.split(':')
                        schedule.time = dt_time(int(h), int(m))
                        schedule.save(update_fields=['time'])
                    except ValueError:
                        errors.append(f'Invalid time for {schedule.slot.label}: "{raw}"')
            if errors:
                for err in errors:
                    messages.error(request, err)
            else:
                messages.success(request, 'Schedule saved.')

        return redirect('foodie_schedule')

    # Auto-seed schedule for users created before the signal was in place
    if not UserMealSchedule.objects.filter(user=request.user).exists():
        for slot in MealTimeSlot.objects.exclude(label='fancy'):
            UserMealSchedule.objects.get_or_create(
                user=request.user, slot=slot,
                defaults={'time': slot.default_time}
            )

    schedules = UserMealSchedule.objects.select_related('slot').filter(
        user=request.user
    ).order_by('time')

    return render(request, 'foodie/meal_schedule.html', {
        'schedules': schedules,
    })


@login_required
def meal_search_autocomplete(request, mealtime):
    q = request.GET.get('q', '').strip()
    if len(q) < 3:
        return JsonResponse([], safe=False)

    slot = get_object_or_404(MealTimeSlot, pk=mealtime)
    selected_ids = userPreference.objects.filter(
        user=request.user, slot=slot
    ).values_list('meal_id', flat=True)

    results = (
        meal.objects.filter(
            Q(created_by=None) | Q(created_by=request.user) | Q(is_public=True),
            name__icontains=q,
        )
        .exclude(id__in=selected_ids)
        .values('id', 'name')[:8]
    )
    return JsonResponse(list(results), safe=False)


# REST API
def foodie_rest(request):
    context = services.suggest(request.user)
    context = serialize_mealtime(context, request)
    return JsonResponse(context)


def all_foodie_rest(request):
    context = services.get_all(request.user)
    context = serialize_all(context, request)
    return JsonResponse(context, safe=False)
