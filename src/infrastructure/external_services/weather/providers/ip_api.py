import logging

import httpx

from ..base import GeolocationProvider

logger = logging.getLogger(__name__)


class IpApiGeolocationProvider(GeolocationProvider):
    """
    IP lookups via https://ip-api.com (free, no API key, HTTP only on the free tier).

    ip-api.com only geolocates by IP, so reverse (coordinate -> place name)
    lookups — used to name a GPS fix — go to https://www.bigdatacloud.com's
    free client reverse-geocode endpoint, and forward (city name -> places)
    searches go to Open-Meteo's free geocoding endpoint. Neither needs an
    API key.
    """

    BASE_URL = 'http://ip-api.com/json/{ip}'
    REVERSE_URL = 'https://api.bigdatacloud.net/data/reverse-geocode-client'
    SEARCH_URL = 'https://geocoding-api.open-meteo.com/v1/search'

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

    def reverse(self, lat, lon):
        try:
            response = httpx.get(
                self.REVERSE_URL,
                params={'latitude': lat, 'longitude': lon, 'localityLanguage': 'en'},
                timeout=8,
            )
            response.raise_for_status()
            data = response.json()

            return {
                'city': data.get('city') or data.get('locality') or '',
                'region': data.get('principalSubdivision', ''),
                'country': data.get('countryName', ''),
            }
        except Exception:
            logger.exception('IpApiGeolocationProvider.reverse failed for (%s, %s)', lat, lon)
            return None

    def search(self, query):
        try:
            response = httpx.get(
                self.SEARCH_URL,
                params={'name': query, 'count': 6, 'language': 'en', 'format': 'json'},
                timeout=8,
            )
            response.raise_for_status()
            results = response.json().get('results') or []

            return [
                {
                    'city': r.get('name', ''),
                    'region': r.get('admin1', ''),
                    'country': r.get('country', ''),
                    'lat': r.get('latitude'),
                    'lon': r.get('longitude'),
                }
                for r in results
                if r.get('latitude') is not None and r.get('longitude') is not None
            ]
        except Exception:
            logger.exception('IpApiGeolocationProvider.search failed for %r', query)
            return []
