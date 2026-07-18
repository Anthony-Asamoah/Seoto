from django.conf import settings

from .providers import IpApiGeolocationProvider, OpenMeteoWeatherProvider

WEATHER_PROVIDERS = {
    'open_meteo': OpenMeteoWeatherProvider,
}

GEOLOCATION_PROVIDERS = {
    'ip_api': IpApiGeolocationProvider,
}


def get_weather_provider():
    provider_cls = WEATHER_PROVIDERS[settings.WEATHER_PROVIDER]
    return provider_cls()


def get_geolocation_provider():
    provider_cls = GEOLOCATION_PROVIDERS[settings.GEOLOCATION_PROVIDER]
    return provider_cls()
