import logging

from .ip_api import IpApiGeolocationProvider
from .open_meteo import OpenMeteoWeatherProvider

# Suppress httpx debug logging so request URLs don't leak into logs.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

__all__ = ['IpApiGeolocationProvider', 'OpenMeteoWeatherProvider']
