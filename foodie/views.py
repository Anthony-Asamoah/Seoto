from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect

from . import the_code
from .models import meal, userPreference
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
    return render(request, 'foodie/foodie.html', context)


def foodie_rest(request):
    context = the_code.suggest(request.user)
    context = serialize_mealtime(context, request)

    return JsonResponse(context)


def all_foodie_rest(request):
    context = the_code.get_all(request.user)
    context = serialize_all(context, request)

    return JsonResponse(context, safe=False)


def foodie_config(request, mealtime=None):
    # Require login to configure per-user preferences
    if not request.user.is_authenticated:
        return HttpResponseBadRequest('Login required to configure preferences')

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
