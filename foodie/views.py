from django.contrib import messages
from django.contrib.auth.decorators import permission_required, login_required
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404

from . import the_code
from .forms import MealOrderForm
from .models import meal, userPreference, MealOrder
from .serializer import serialize_mealtime, serialize_all

MEALTIME_FIELDS = {
    'breakfast': 'isBreakfast',
    'brunch': 'isBrunch',
    'lunch': 'isLunch',
    'dinner': 'isDinner',
    'extra': 'isExtra',
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
        try:
            selected_ids = [int(x) for x in selected_ids]
        except ValueError:
            selected_ids = []

        # Update user preferences for this mealtime
        meals_qs = meal.objects.all()
        for m in meals_qs:
            pref, _created = userPreference.objects.get_or_create(
                user=request.user, meal=m, defaults={'isAvailable': True}
            )
            setattr(pref, field, m.id in selected_ids)
            pref.save(update_fields=[field])

        # After saving, redirect to the same page to avoid resubmission
        return redirect('foodie_config_time', mealtime=mt)

    meals_qs = meal.objects.all().order_by('name')
    # Build list of ids currently selected for this mealtime for current user
    selected_ids = list(
        userPreference.objects.filter(user=request.user, **{field: True}).values_list('meal_id', flat=True)
    )
    context = {
        'mealtime': mt,
        'mealtime_readable': mt.capitalize(),
        'field': field,
        'meals': meals_qs,
        'selected_ids': selected_ids,
        'mealtime_fields': MEALTIME_FIELDS,
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


# REST API
def foodie_rest(request):
    context = the_code.suggest(request.user)
    context = serialize_mealtime(context, request)

    return JsonResponse(context)


def all_foodie_rest(request):
    context = the_code.get_all(request.user)
    context = serialize_all(context, request)

    return JsonResponse(context, safe=False)
