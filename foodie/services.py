from datetime import datetime
from random import randint

from .models import meal, userPreference

MEALTIME_FIELDS = {
    'Breakfast': 'isBreakfast',
    'Brunch': 'isBrunch',
    'Lunch': 'isLunch',
    'Dinner': 'isDinner',
    'Extra': 'isExtra',
}


def _current_mealtime():
    hour = datetime.now().hour
    if 4 <= hour < 10:
        return 'Breakfast'
    if 10 <= hour < 13:
        return 'Brunch'
    if 13 <= hour < 18:
        return 'Lunch'
    if 18 <= hour < 21:
        return 'Dinner'
    if 21 <= hour < 24:
        return 'Extra'
    return 'Fasting'


def suggest(user=None):
    context = {}
    mealtime = _current_mealtime()

    # Default placeholders if no preferences
    available_meals = []

    if user and user.is_authenticated:
        field = MEALTIME_FIELDS.get(mealtime)
        if field:
            prefs = userPreference.objects.select_related('meal').filter(
                user=user, isAvailable=True, **{field: True}
            )
            available_meals = [p.meal for p in prefs]
        fancy_prefs = userPreference.objects.select_related('meal').filter(
            user=user, isAvailable=True, isFancy=True
        )
        fancy_meals = [p.meal for p in fancy_prefs]
    else:
        # If no user, fallback to all meals without filtering; no flags to filter by
        available_meals = list(meal.objects.all())
        fancy_meals = []

    if available_meals:
        suggestion1 = available_meals[randint(0, len(available_meals) - 1)]
        suggestion2 = available_meals[randint(0, len(available_meals) - 1)]

        if len(available_meals) > 1:
            while suggestion2 == suggestion1:
                suggestion2 = available_meals[randint(0, len(available_meals) - 1)]

        context = {
            'mealtime': mealtime,
            'option_1': suggestion1,
            'option_2': suggestion2,
        }

        if fancy_meals:
            fancy = fancy_meals[randint(0, len(fancy_meals) - 1)]
            context.update({'fancy': fancy})

    return context


def get_all(user=None):
    if user and user.is_authenticated:
        prefs = userPreference.objects.select_related('meal').filter(user=user, isAvailable=True)
        return [
            {
                'id': p.meal.id,
                'name': p.meal.name,
                'description': p.meal.description,
                'ingredients': p.meal.ingredients,
                'nutrients': p.meal.nutrients,
                'benefits': p.meal.benefits,
                'cooking_duration': p.meal.cooking_duration,
                'main_img': getattr(p.meal.main_img, 'name', ''),
                'img_1': getattr(p.meal.img_1, 'name', ''),
                'img_2': getattr(p.meal.img_2, 'name', ''),
                'img_3': getattr(p.meal.img_3, 'name', ''),
            }
            for p in prefs
        ]
    # Fallback to all meals if user not available
    return meal.objects.all().values()
