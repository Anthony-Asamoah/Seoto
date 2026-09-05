import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx

from ..base import WeatherProvider
from .wmo import describe

logger = logging.getLogger(__name__)


class OpenMeteoWeatherProvider(WeatherProvider):
    """https://open-meteo.com — free, no API key required."""

    BASE_URL = 'https://api.open-meteo.com/v1/forecast'

    DAILY_DAYS = 5

    def get_forecast(self, lat, lon):
        try:
            response = httpx.get(
                self.BASE_URL,
                params={
                    'latitude': lat,
                    'longitude': lon,
                    'current': 'temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m',
                    'hourly': 'temperature_2m,weather_code',
                    'daily': 'weather_code,temperature_2m_max,temperature_2m_min',
                    'forecast_days': self.DAILY_DAYS,
                    'timezone': 'auto',
                },
                timeout=8,
            )
            response.raise_for_status()
            data = response.json()
            current = data['current']
            daily = data['daily']
            hourly = data.get('hourly') or {}
            timezone_name = data.get('timezone')
            code = current.get('weather_code')
            text, icon = describe(code)

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
                'timezone': timezone_name,
                'daily': self._build_daily(daily, hourly, timezone_name),
            }
        except Exception:
            logger.exception('OpenMeteoWeatherProvider.get_forecast failed for (%s, %s)', lat, lon)
            return None

    @staticmethod
    def _group_hourly_by_date(hourly):
        times = hourly.get('time') or []
        temps = hourly.get('temperature_2m') or []
        codes = hourly.get('weather_code') or []

        by_date = {}
        for i, timestamp in enumerate(times):
            date_str, _, hour_str = timestamp.partition('T')
            hour_code = codes[i] if i < len(codes) else None
            hour_text, hour_icon = describe(hour_code)
            by_date.setdefault(date_str, []).append({
                'time': timestamp,
                'hour_label': hour_str,
                'temperature': temps[i] if i < len(temps) else None,
                'condition_text': hour_text,
                'icon': hour_icon,
            })
        return by_date

    @classmethod
    def _build_daily(cls, daily, hourly, timezone_name):
        dates = daily.get('time') or []
        codes = daily.get('weather_code') or []
        highs = daily.get('temperature_2m_max') or []
        lows = daily.get('temperature_2m_min') or []
        hourly_by_date = cls._group_hourly_by_date(hourly)

        current_hour_mark = None
        if timezone_name:
            try:
                current_hour_mark = datetime.now(ZoneInfo(timezone_name)).strftime('%Y-%m-%dT%H:00')
            except Exception:
                current_hour_mark = None

        days = []
        for i, date_str in enumerate(dates):
            day_code = codes[i] if i < len(codes) else None
            day_text, day_icon = describe(day_code)
            day_label = 'Today' if i == 0 else datetime.strptime(date_str, '%Y-%m-%d').strftime('%a')

            day_hours = hourly_by_date.get(date_str, [])
            if i == 0 and current_hour_mark:
                day_hours = [h for h in day_hours if h['time'] >= current_hour_mark]

            days.append({
                'date': date_str,
                'day_label': day_label,
                'high': highs[i] if i < len(highs) else None,
                'low': lows[i] if i < len(lows) else None,
                'condition_text': day_text,
                'icon': day_icon,
                'hourly': day_hours,
            })
        return days
