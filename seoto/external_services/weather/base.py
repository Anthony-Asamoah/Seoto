"""
Provider interfaces for the weather widget.

Concrete implementations live in `providers.py`; `factory.py` picks one at
runtime from settings.WEATHER_PROVIDER / settings.GEOLOCATION_PROVIDER, so a
provider can be swapped out without touching any call site.
"""
from abc import ABC, abstractmethod
from typing import Optional


class WeatherProvider(ABC):
    @abstractmethod
    def get_forecast(self, lat: float, lon: float) -> Optional[dict]:
        """
        Return a normalized forecast dict:
            {temperature, feels_like, humidity, wind_speed,
             condition_code, condition_text, icon, high, low, timezone,
             daily: [{date, day_label, high, low, condition_text, icon,
                      hourly: [{time, hour_label, temperature,
                                condition_text, icon}, ...]}, ...]}
        or None if the forecast could not be retrieved.
        """


class GeolocationProvider(ABC):
    @abstractmethod
    def locate(self, ip: str) -> Optional[dict]:
        """
        Return a normalized dict: {lat, lon, city, region, country}
        or None if the IP could not be located.
        """

    @abstractmethod
    def reverse(self, lat: float, lon: float) -> Optional[dict]:
        """
        Return a normalized dict: {city, region, country} for a coordinate
        pair (used to name a GPS fix), or None if it could not be resolved.
        """

    @abstractmethod
    def search(self, query: str) -> list:
        """
        Return a list of matching places for a free-text city query, each a
        normalized dict {city, region, country, lat, lon}. Empty list when
        there are no matches or the lookup failed.
        """
