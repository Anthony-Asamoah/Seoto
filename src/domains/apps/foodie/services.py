from datetime import datetime
from random import choice, sample

from .models import meal, userPreference, UserMealSchedule, DailyMealSuggestion, MealTimeSlot


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


def _build_context(mealtime, option_1_obj, option_2_obj, fancy_obj):
    option_1 = _meal_data(option_1_obj)
    option_2 = _meal_data(option_2_obj) if option_2_obj else None

    if option_2:
        names = f"{option_1['name'].lower()} or {option_2['name'].lower()}"
    else:
        names = option_1['name'].lower()

    if mealtime:
        suggestion_text = f"It's time for {mealtime.lower()}, so I suggest {names}."
    else:
        suggestion_text = f"Unfortunately you will be going to bed soon. Have {names} for now."

    context = {
        'mealtime': mealtime,
        'option_1': option_1,
        'option_2': option_2,
        'suggestion_text': suggestion_text,
    }
    if fancy_obj:
        fancy = _meal_data(fancy_obj)
        context['fancy'] = fancy
        context['fancy_text'] = f"Otherwise let's get some {fancy['name'].lower()}."
    return context


def _pick_options(pool, exclude_ids):
    """Pick up to 2 distinct meals from pool, preferring those whose id is not in exclude_ids.
    Falls back to the full pool if the filtered pool is too small. Returns (m1, m2_or_None)."""
    if not pool:
        return None, None

    filtered = [m for m in pool if m.id not in exclude_ids]
    if len(filtered) >= 2:
        picks = sample(filtered, 2)
        return picks[0], picks[1]
    if len(filtered) == 1:
        first = filtered[0]
        # Need a second from the rest of the pool (allow used-today repeat) but distinct from first
        rest = [m for m in pool if m.id != first.id]
        second = choice(rest) if rest else None
        return first, second
    # filtered empty — allow repeats from full pool
    if len(pool) >= 2:
        picks = sample(pool, 2)
        return picks[0], picks[1]
    return pool[0], None


def _pick_fancy(pool, exclude_ids):
    if not pool:
        return None
    filtered = [m for m in pool if m.id not in exclude_ids]
    if filtered:
        return choice(filtered)
    return choice(pool)


def _session_key(today, mealtime):
    return f"{today.isoformat()}:{mealtime}"


def _session_used_ids(session, today):
    prefix = f"{today.isoformat()}:"
    used = set()
    store = session.get('foodie_suggestion', {})
    for key, val in store.items():
        if key.startswith(prefix):
            for fld in ('option_1', 'option_2', 'fancy'):
                mid = val.get(fld)
                if mid:
                    used.add(mid)
    return used


def _prune_session(session, today):
    """Drop session cache entries from prior dates."""
    store = session.get('foodie_suggestion', {})
    prefix = f"{today.isoformat()}:"
    pruned = {k: v for k, v in store.items() if k.startswith(prefix)}
    if pruned != store:
        session['foodie_suggestion'] = pruned
        session.modified = True


def suggest(user=None, slot=None, request=None):
    """Return a stable per-(user, date, slot) meal suggestion.

    Within a single mealtime on a given day, repeated calls return the same picks.
    Across mealtimes within the same day, picks avoid meals already shown.
    Anonymous suggestions are cached in the request session.
    """
    if user is None and request is not None:
        user = request.user

    mealtime = slot.label if slot else _current_mealtime(user)
    today = datetime.now().date()

    is_auth = bool(user and user.is_authenticated)

    # 1. Cache lookup
    if is_auth and mealtime:
        cached = (
            DailyMealSuggestion.objects
            .select_related('option_1', 'option_2', 'fancy')
            .filter(user=user, date=today, slot_id=mealtime)
            .first()
        )
        if cached:
            return _build_context(mealtime, cached.option_1, cached.option_2, cached.fancy)

    if not is_auth and request is not None and mealtime:
        _prune_session(request.session, today)
        store = request.session.get('foodie_suggestion', {})
        cached = store.get(_session_key(today, mealtime))
        if cached:
            try:
                m1 = meal.objects.get(pk=cached['option_1'])
                m2 = meal.objects.filter(pk=cached.get('option_2')).first() if cached.get('option_2') else None
                fm = meal.objects.filter(pk=cached.get('fancy')).first() if cached.get('fancy') else None
                return _build_context(mealtime, m1, m2, fm)
            except meal.DoesNotExist:
                pass  # stale cache; regenerate

    # 2. Build pools
    available_meals = []
    fancy_pool = []

    if is_auth:
        if mealtime:
            prefs = userPreference.objects.select_related('meal').filter(
                user=user, isAvailable=True, slot_id=mealtime, meal__is_fancy=False
            )
            available_meals = [p.meal for p in prefs]
        fancy_prefs = userPreference.objects.select_related('meal').filter(
            user=user, isAvailable=True, slot_id='fancy'
        )
        fancy_pool = [p.meal for p in fancy_prefs]
    else:
        if mealtime:
            available_meals = list(meal.objects.filter(
                is_fancy=False, created_by=None,
                categories__icontains=f'"{mealtime}"'
            ))
        fancy_pool = list(meal.objects.filter(is_fancy=True, created_by=None))

    # 3. Determine "used today" exclusion set
    if is_auth:
        used_ids = set()
        for row in DailyMealSuggestion.objects.filter(user=user, date=today).values(
            'option_1_id', 'option_2_id', 'fancy_id'
        ):
            for v in row.values():
                if v:
                    used_ids.add(v)
    elif request is not None:
        used_ids = _session_used_ids(request.session, today)
    else:
        used_ids = set()

    # 4. Pick options
    option_1_obj, option_2_obj = _pick_options(available_meals, used_ids)
    if option_1_obj is None:
        # No meals at all for this slot — return empty context (matches prior behavior)
        # but still try fancy.
        fancy_exclude = used_ids.copy()
        fancy_obj = _pick_fancy(fancy_pool, fancy_exclude)
        if fancy_obj is None:
            return {}
        # Build a fancy-only context (no main options).
        ctx = {'mealtime': mealtime}
        ctx['fancy'] = _meal_data(fancy_obj)
        ctx['fancy_text'] = f"Otherwise let's get some {ctx['fancy']['name'].lower()}."
        return ctx

    # 5. Pick fancy (excluding used + chosen options)
    fancy_exclude = set(used_ids)
    fancy_exclude.add(option_1_obj.id)
    if option_2_obj:
        fancy_exclude.add(option_2_obj.id)
    fancy_obj = _pick_fancy(fancy_pool, fancy_exclude)

    # 6. Persist
    if is_auth and mealtime:
        try:
            slot_obj = MealTimeSlot.objects.get(pk=mealtime)
            DailyMealSuggestion.objects.update_or_create(
                user=user, date=today, slot=slot_obj,
                defaults={
                    'option_1': option_1_obj,
                    'option_2': option_2_obj,
                    'fancy': fancy_obj,
                },
            )
        except MealTimeSlot.DoesNotExist:
            pass
    elif not is_auth and request is not None and mealtime:
        store = request.session.get('foodie_suggestion', {})
        store[_session_key(today, mealtime)] = {
            'option_1': option_1_obj.id,
            'option_2': option_2_obj.id if option_2_obj else None,
            'fancy': fancy_obj.id if fancy_obj else None,
        }
        request.session['foodie_suggestion'] = store
        request.session.modified = True

    return _build_context(mealtime, option_1_obj, option_2_obj, fancy_obj)


def send_due_meal_notifications(current_hour=None):
    """Send a meal suggestion push notification to every user whose schedule is due this hour.

    Finds all UserMealSchedule rows whose time falls in ``current_hour`` (defaults to the
    current local hour), and for each distinct user with an active push subscription, sends a
    suggestion built via :func:`suggest`. Returns ``{'sent': int, 'skipped': int}``.
    """
    # Lazy import to avoid an import-time foodie -> pwa coupling at module load.
    from domains.pwa.models import PushSubscription
    from domains.pwa.services import send_push_notification

    if current_hour is None:
        current_hour = datetime.now().hour

    due_schedules = UserMealSchedule.objects.select_related('user', 'slot').filter(
        time__hour=current_hour,
    )

    sent_count = 0
    skipped_count = 0
    seen_users = set()

    for schedule in due_schedules:
        user = schedule.user

        if user.id in seen_users:
            continue
        seen_users.add(user.id)

        if not PushSubscription.objects.filter(user=user, is_active=True).exists():
            skipped_count += 1
            continue

        context = suggest(user, slot=schedule.slot)
        if not context.get('option_1'):
            skipped_count += 1
            continue

        option_1 = context['option_1']
        option_2 = context.get('option_2')
        mealtime = context.get('mealtime', schedule.slot.label)

        title = f"{mealtime.capitalize()} Time!"
        if option_2 and option_2['name'] != option_1['name']:
            body = f"How about {option_1['name']} or {option_2['name']}?"
        else:
            body = f"How about {option_1['name']}?"

        result = send_push_notification(user=user, title=title, body=body, url='/foodie/')

        if result:
            sent_count += 1
        else:
            skipped_count += 1

    return {'sent': sent_count, 'skipped': skipped_count}


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
