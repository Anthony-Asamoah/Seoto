from datetime import datetime
from random import choice, sample

from .models import meal, userPreference, UserMealSchedule


def _meal_data(m):
    """Serialize a meal instance to a plain dict with description and image URLs."""
    def _url(field):
        if field and getattr(field, 'name', None):
            try:
                return field.url
            except ValueError:
                return None
        return None

    return {
        'id': m.id,
        'name': m.name,
        'description': m.description,
        'main_img': _url(m.main_img),
        'img_1': _url(m.img_1),
        'img_2': _url(m.img_2),
        'img_3': _url(m.img_3),
    }


def _current_mealtime(user=None):
    """
    Return the label of the current meal time slot.
    For authenticated users, finds the slot whose scheduled time is within 30 minutes of now.
    Falls back to hour-based heuristic for unauthenticated users or when no slot matches.
    """
    now = datetime.now()
    now_minutes = now.hour * 60 + now.minute

    if user and user.is_authenticated:
        schedules = list(
            UserMealSchedule.objects
            .select_related('slot')
            .filter(user=user)
            .exclude(slot__label='fancy')
        )
        if schedules:
            schedules.sort(key=lambda sch: (sch.time.hour, sch.time.minute))
            current = None
            for sch in schedules:
                slot_minutes = sch.time.hour * 60 + sch.time.minute
                if slot_minutes <= now_minutes:
                    current = sch
                else:
                    break
            if current is None:
                current = schedules[-1]
            return current.slot.label

    # Fallback: hour-based heuristic
    hour = now.hour
    if 4 <= hour < 10:
        return 'breakfast'
    if 10 <= hour < 13:
        return 'lunch'
    if 13 <= hour < 18:
        return 'dinner'
    if 18 <= hour < 21:
        return 'snack'
    return None


def suggest(user=None, slot=None):
    context = {}
    mealtime = slot.label if slot else _current_mealtime(user)
    available_meals = []
    fancy_meal = None

    if user and user.is_authenticated:
        if mealtime:
            prefs = userPreference.objects.select_related('meal').filter(
                user=user, isAvailable=True, slot_id=mealtime, meal__is_fancy=False
            )
            available_meals = [p.meal for p in prefs]

        # Fancy: meals the user has added to their 'fancy' pseudo-slot
        fancy_prefs = userPreference.objects.select_related('meal').filter(
            user=user, isAvailable=True, slot_id='fancy'
        )
        fancy_pool = [p.meal for p in fancy_prefs]
        if fancy_pool:
            fancy_meal = choice(fancy_pool)
    else:
        if mealtime:
            available_meals = list(meal.objects.filter(
                is_fancy=False, created_by=None,
                categories__icontains=f'"{mealtime}"'
            ))
        else:
            available_meals = []
        fancy_pool = list(meal.objects.filter(is_fancy=True, created_by=None))
        if fancy_pool:
            fancy_meal = choice(fancy_pool)

    if available_meals:
        picks = sample(available_meals, min(2, len(available_meals)))
        option_1 = _meal_data(picks[0])
        option_2 = _meal_data(picks[1] if len(picks) > 1 else picks[0])

        if mealtime:
            suggestion_text = (
                f"It's time for {mealtime.lower()}, so I suggest "
                f"{option_1['name'].lower()} or {option_2['name'].lower()}."
            )
        else:
            suggestion_text = (
                f"Unfortunately you will be going to bed soon. "
                f"Have {option_1['name'].lower()} or {option_2['name'].lower()} for now."
            )

        context = {
            'mealtime': mealtime,
            'option_1': option_1,
            'option_2': option_2,
            'suggestion_text': suggestion_text,
        }
        if fancy_meal:
            fancy = _meal_data(fancy_meal)
            context['fancy'] = fancy
            context['fancy_text'] = f"Otherwise let's get some {fancy['name'].lower()}."

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
    return meal.objects.filter(created_by=None, is_public=True).values()
