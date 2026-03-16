from django.contrib import messages
from django.contrib.auth.decorators import permission_required, login_required
from django.db.models import Q
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods

from . import services
from .forms import MealOrderForm, UserMealForm
from .models import meal, userPreference, MealOrder, MealTimeSlot, UserMealSchedule
from .serializer import serialize_mealtime, serialize_all
from utils.paginator import apply_pagination


def foodie(request):
    context = services.suggest(request.user)
    context['can_order'] = True if request.user.has_perm('foodie.view_mealorder') else False
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
        selected_ids = request.POST.getlist('selected_meals')
        page_meal_ids = request.POST.getlist('page_meal_ids')
        try:
            selected_ids = [int(x) for x in selected_ids]
            page_meal_ids = [int(x) for x in page_meal_ids]
        except ValueError:
            selected_ids = []
            page_meal_ids = []

        for m in meal.objects.filter(id__in=page_meal_ids):
            if m.id in selected_ids:
                userPreference.objects.get_or_create(
                    user=request.user, meal=m, slot=slot,
                    defaults={'isAvailable': True}
                )
            else:
                userPreference.objects.filter(user=request.user, meal=m, slot=slot).delete()

        redirect_url = f'/foodie/config/{mealtime}'
        qs = request.POST.get('redirect_qs', '')
        if qs:
            redirect_url += f'?{qs}'
        return redirect(redirect_url)

    search_query = request.GET.get('search', '').strip()
    meals_qs = meal.objects.filter(
        Q(created_by=None) | Q(created_by=request.user) | Q(is_public=True)
    ).order_by('name')
    if search_query:
        meals_qs = meals_qs.filter(name__icontains=search_query)

    page_obj = apply_pagination(meals_qs, request.GET.get('page'), 13)
    selected_ids = list(
        userPreference.objects.filter(user=request.user, slot=slot).values_list('meal_id', flat=True)
    )
    query_params = {'search': search_query} if search_query else {}

    context = {
        'mealtime': mealtime,
        'mealtime_readable': slot.label.capitalize(),
        'slot': slot,
        'slots': slots,
        'meals': page_obj,
        'selected_ids': selected_ids,
        'search_query': search_query,
        'query_params': query_params,
    }
    return render(request, 'foodie/foodie_config.html', context)


@login_required
@permission_required('foodie.view_mealorder', login_url='login', raise_exception=True)
def orders_list(request):
    orders = MealOrder.objects.filter(user=request.user).select_related('meal').order_by('-date_ordered')
    return render(request, 'foodie/orders_list.html', {'orders': orders})


@login_required
@permission_required('foodie.add_mealorder', login_url='login', raise_exception=True)
def order_create(request):
    if request.method == 'POST':
        form = MealOrderForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.user = request.user
            order.save()
            return redirect('foodie_orders')
    else:
        form = MealOrderForm()
    return render(request, 'foodie/order_form.html', {'form': form, 'is_edit': False})


@login_required
def order_edit(request, pk: int):
    order = get_object_or_404(MealOrder, pk=pk)
    if order.user_id != request.user.id:
        return HttpResponseForbidden('You cannot edit this order.')
    if not order.not_available:
        messages.warning(request, 'This order cannot be edited at the moment.')
        return redirect('foodie_orders')

    if request.method == 'POST':
        form = MealOrderForm(request.POST, instance=order)
        if form.is_valid():
            updated_order = form.save()
            updated_order.reset_to_pending()
            messages.success(request, 'Order updated and set back to pending.')
            return redirect('foodie_orders')
    else:
        form = MealOrderForm(instance=order)

    return render(request, 'foodie/order_form.html', {'form': form, 'is_edit': True, 'order': order})


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


# REST API
def foodie_rest(request):
    context = services.suggest(request.user)
    context = serialize_mealtime(context, request)
    return JsonResponse(context)


def all_foodie_rest(request):
    context = services.get_all(request.user)
    context = serialize_all(context, request)
    return JsonResponse(context, safe=False)
