from django.contrib import messages
from django.contrib.auth.decorators import permission_required, login_required
from django.db.models import Q
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods

from . import services
from .forms import MealOrderForm, UserMealForm
from .models import meal, userPreference, MealOrder
from .serializer import serialize_mealtime, serialize_all
from utils.paginator import apply_pagination

MEALTIME_FIELDS = {
    'breakfast': 'isBreakfast',
    'brunch': 'isBrunch',
    'lunch': 'isLunch',
    'dinner': 'isDinner',
    'extra': 'isExtra',
    'fancy': 'isFancy',
}


def foodie(request):
    context = the_code.suggest(request.user)
    context['can_order'] = True if request.user.has_perm('foodie.view_mealorder') else False

    return render(request, 'foodie/foodie.html', context)


@login_required
def foodie_config(request, mealtime=None):
    # If no specific mealtime provided, show landing page with links
    if mealtime is None:
        return render(request, 'foodie/foodie_config.html', {
            'mealtime': None,
            'mealtime_fields': MEALTIME_FIELDS,
            'meals': [],
        })

    mt = str(mealtime).lower()
    if mt not in MEALTIME_FIELDS:
        return HttpResponseBadRequest('Unknown mealtime')

    field = MEALTIME_FIELDS[mt]

    if request.method == 'POST':
        selected_ids = request.POST.getlist('selected_meals')
        page_meal_ids = request.POST.getlist('page_meal_ids')
        try:
            selected_ids = [int(x) for x in selected_ids]
            page_meal_ids = [int(x) for x in page_meal_ids]
        except ValueError:
            selected_ids = []
            page_meal_ids = []

        # Only update meals that were visible on the submitted page
        for m in meal.objects.filter(id__in=page_meal_ids):
            pref, _created = userPreference.objects.get_or_create(
                user=request.user, meal=m, defaults={'isAvailable': True}
            )
            setattr(pref, field, m.id in selected_ids)
            pref.save(update_fields=[field])

        redirect_url = f'/foodie/config/{mt}'
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
        userPreference.objects.filter(user=request.user, **{field: True}).values_list('meal_id', flat=True)
    )
    query_params = {'search': search_query} if search_query else {}

    context = {
        'mealtime': mt,
        'mealtime_readable': mt.capitalize(),
        'field': field,
        'meals': page_obj,
        'selected_ids': selected_ids,
        'mealtime_fields': MEALTIME_FIELDS,
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
            # Reset statuses back to pending and clear not_available
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
    pref, _ = userPreference.objects.get_or_create(user=request.user, meal=m, defaults={'isAvailable': True})

    if request.method == 'POST':
        form = UserMealForm(request.POST, request.FILES, instance=m)
        if form.is_valid():
            form.save()
            selected_times = request.POST.getlist('mealtimes')
            for mt, field in MEALTIME_FIELDS.items():
                setattr(pref, field, mt in selected_times)
            pref.save(update_fields=list(MEALTIME_FIELDS.values()))
            messages.success(request, f'"{m.name}" updated.')
            return redirect('foodie_my_meals')
    else:
        form = UserMealForm(instance=m)

    active_mealtimes = [mt for mt, field in MEALTIME_FIELDS.items() if getattr(pref, field)]
    return render(request, 'foodie/meal_form.html', {
        'form': form,
        'is_edit': True,
        'meal_obj': m,
        'mealtime_fields': MEALTIME_FIELDS,
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


# REST API
def foodie_rest(request):
    context = the_code.suggest(request.user)
    context = serialize_mealtime(context, request)

    return JsonResponse(context)


def all_foodie_rest(request):
    context = the_code.get_all(request.user)
    context = serialize_all(context, request)

    return JsonResponse(context, safe=False)
