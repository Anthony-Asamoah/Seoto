import logging

import httpx

from .base import GeolocationProvider, WeatherProvider

logger = logging.getLogger(__name__)

# Suppress httpx debug logging so request URLs don't leak into logs.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# WMO weather codes (used by Open-Meteo) -> (human text, Font Awesome icon class)
_WMO_CONDITIONS = {
    0: ('Clear sky', 'fa-sun'),
    1: ('Mainly clear', 'fa-sun'),
    2: ('Partly cloudy', 'fa-cloud-sun'),
    3: ('Overcast', 'fa-cloud'),
    45: ('Fog', 'fa-smog'),
    48: ('Depositing rime fog', 'fa-smog'),
    51: ('Light drizzle', 'fa-cloud-rain'),
    53: ('Drizzle', 'fa-cloud-rain'),
    55: ('Dense drizzle', 'fa-cloud-rain'),
    56: ('Freezing drizzle', 'fa-cloud-rain'),
    57: ('Freezing drizzle', 'fa-cloud-rain'),
    61: ('Slight rain', 'fa-cloud-rain'),
    63: ('Rain', 'fa-cloud-showers-heavy'),
    65: ('Heavy rain', 'fa-cloud-showers-heavy'),
    66: ('Freezing rain', 'fa-cloud-showers-heavy'),
    67: ('Freezing rain', 'fa-cloud-showers-heavy'),
    71: ('Slight snow', 'fa-snowflake'),
    73: ('Snow', 'fa-snowflake'),
    75: ('Heavy snow', 'fa-snowflake'),
    77: ('Snow grains', 'fa-snowflake'),
    80: ('Slight showers', 'fa-cloud-rain'),
    81: ('Showers', 'fa-cloud-showers-heavy'),
    82: ('Violent showers', 'fa-cloud-showers-heavy'),
    85: ('Slight snow showers', 'fa-snowflake'),
    86: ('Heavy snow showers', 'fa-snowflake'),
    95: ('Thunderstorm', 'fa-bolt'),
    96: ('Thunderstorm with hail', 'fa-bolt'),
    99: ('Thunderstorm with heavy hail', 'fa-bolt'),
}
_DEFAULT_CONDITION = ('Unknown', 'fa-cloud')


class OpenMeteoWeatherProvider(WeatherProvider):
    """https://open-meteo.com — free, no API key required."""

    BASE_URL = 'https://api.open-meteo.com/v1/forecast'

    def get_forecast(self, lat, lon):
        try:
            response = httpx.get(
                self.BASE_URL,
                params={
                    'latitude': lat,
                    'longitude': lon,
                    'current': 'temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m',
                    'daily': 'temperature_2m_max,temperature_2m_min',
                    'timezone': 'auto',
                },
                timeout=8,
            )
            response.raise_for_status()
            data = response.json()
            current = data['current']
            daily = data['daily']
            code = current.get('weather_code')
            text, icon = _WMO_CONDITIONS.get(code, _DEFAULT_CONDITION)

            return {
                'temperature': current.get('temperature_2m'),
                'feels_like': current.get('apparent_temperature'),
                'humidity': current.get('relative_humidity_2m'),
                'wind_speed': current.get('wind_speed_10m'),
                'condition_code': code,
                'condition_text': text,
                'icon': icon,
                'high': (daily.get('temperature_2m_max') or [None])[0],
                'low': (daily.get('temperature_2m_min') or [None])[0],
                'timezone': data.get('timezone'),
            }
        except Exception:
            logger.exception('OpenMeteoWeatherProvider.get_forecast failed for (%s, %s)', lat, lon)
            return None


class IpApiGeolocationProvider(GeolocationProvider):
    """https://ip-api.com — free, no API key required (HTTP only on the free tier)."""

    BASE_URL = 'http://ip-api.com/json/{ip}'

    def locate(self, ip):
        try:
            response = httpx.get(
                self.BASE_URL.format(ip=ip),
                params={'fields': 'status,message,lat,lon,city,regionName,country'},
                timeout=8,
            )
            response.raise_for_status()
            data = response.json()
            if data.get('status') != 'success':
                logger.info('IpApiGeolocationProvider could not locate IP %s: %s', ip, data.get('message'))
                return None

            return {
                'lat': data['lat'],
                'lon': data['lon'],
                'city': data.get('city', ''),
                'region': data.get('regionName', ''),
                'country': data.get('country', ''),
            }
        except Exception:
            logger.exception('IpApiGeolocationProvider.locate failed for IP %s', ip)
            return None
