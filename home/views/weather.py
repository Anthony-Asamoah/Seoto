import logging

from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from home.utils import get_client_ip
from seoto.external_services.weather import get_geolocation_provider, get_weather_provider

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 600
REVERSE_GEOCODE_CACHE_TTL_SECONDS = 3600


@require_http_methods(["GET"])
def weather_forecast(request):
    """
    Return current weather for the requester.

    Defaults to IP-based geolocation; pass ?lat=&lon= (from the browser's
    Geolocation API) to use a precise GPS fix instead.
    """
    lat = request.GET.get('lat')
    lon = request.GET.get('lon')

    try:
        if lat and lon and request.GET.get('source') == 'search':
            # A place picked from search already carries its own name, so
            # trust the supplied label instead of spending a reverse lookup.
            lat, lon = float(lat), float(lon)
            location = {
                'city': request.GET.get('city', ''),
                'region': request.GET.get('region', ''),
                'country': request.GET.get('country', ''),
            }
            source = 'search'
        elif lat and lon:
            lat, lon = float(lat), float(lon)
            reverse_cache_key = f'weather:reverse:{round(lat, 3)}:{round(lon, 3)}'
            location = cache.get(reverse_cache_key)
            if location is None:
                location = get_geolocation_provider().reverse(lat, lon)
                if location is not None:
                    cache.set(reverse_cache_key, location, REVERSE_GEOCODE_CACHE_TTL_SECONDS)
            if location is None:
                location = {'city': '', 'region': '', 'country': ''}
            source = 'gps'
        else:
            ip = get_client_ip(request)
            cache_key = f'weather:geo:{ip}'
            location = cache.get(cache_key)
            if location is None:
                location = get_geolocation_provider().locate(ip)
                if location is not None:
                    cache.set(cache_key, location, CACHE_TTL_SECONDS)

            if location is None:
                return JsonResponse(
                    {'error': 'Could not determine your location from your IP address.'},
                    status=503,
                )
            lat, lon = location['lat'], location['lon']
            source = 'ip'

        weather_cache_key = f'weather:forecast:{round(lat, 2)}:{round(lon, 2)}'
        weather = cache.get(weather_cache_key)
        if weather is None:
            weather = get_weather_provider().get_forecast(lat, lon)
            if weather is not None:
                cache.set(weather_cache_key, weather, CACHE_TTL_SECONDS)

        if weather is None:
            return JsonResponse({'error': 'Weather service is currently unavailable.'}, status=503)

        return JsonResponse({
            'source': source,
            'location': location,
            'weather': weather,
        })
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Invalid coordinates.'}, status=400)
    except Exception:
        logger.exception('weather_forecast failed')
        return JsonResponse({'error': 'Could not load weather.'}, status=500)


SEARCH_CACHE_TTL_SECONDS = 3600


@require_http_methods(["GET"])
def weather_search(request):
    """Return matching places for a free-text city query (for the location search)."""
    query = (request.GET.get('q') or '').strip()
    if len(query) < 2:
        return JsonResponse({'results': []})

    try:
        cache_key = f'weather:search:{query.lower()}'
        results = cache.get(cache_key)
        if results is None:
            results = get_geolocation_provider().search(query)
            cache.set(cache_key, results, SEARCH_CACHE_TTL_SECONDS)
        return JsonResponse({'results': results})
    except Exception:
        logger.exception('weather_search failed for %r', query)
        return JsonResponse({'error': 'Could not search locations.', 'results': []}, status=500)
