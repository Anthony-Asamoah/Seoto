"""WMO weather codes (used by Open-Meteo) -> (human text, Font Awesome icon class)."""

WMO_CONDITIONS = {
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

DEFAULT_CONDITION = ('Unknown', 'fa-cloud')


def describe(code):
    """Text and icon for a WMO code, falling back to the unknown pair."""
    return WMO_CONDITIONS.get(code, DEFAULT_CONDITION)
