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
             condition_code, condition_text, icon, high, low, timezone}
        or None if the forecast could not be retrieved.
        """


class GeolocationProvider(ABC):
    @abstractmethod
    def locate(self, ip: str) -> Optional[dict]:
        """
        Return a normalized dict: {lat, lon, city, region, country}
        or None if the IP could not be located.
        """
