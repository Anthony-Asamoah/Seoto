from django.test import SimpleTestCase

from infrastructure.external_services.weather.providers import OpenMeteoWeatherProvider
from infrastructure.external_services.weather.providers.wmo import DEFAULT_CONDITION, describe


class BuildDailyTests(SimpleTestCase):
    def setUp(self):
        self.daily = {
            'time': ['2026-07-18', '2026-07-19'],
            'weather_code': [3, 1],
            'temperature_2m_max': [30.0, 31.0],
            'temperature_2m_min': [24.0, 23.5],
        }
        self.hourly = {
            'time': [
                '2026-07-18T00:00', '2026-07-18T06:00', '2026-07-18T12:00', '2026-07-18T18:00',
                '2026-07-19T00:00', '2026-07-19T12:00',
            ],
            'weather_code': [3, 3, 2, 1, 1, 0],
            'temperature_2m': [23.0, 24.0, 29.0, 26.0, 22.5, 28.0],
        }

    def test_groups_hourly_readings_under_their_date(self):
        days = OpenMeteoWeatherProvider._build_daily(self.daily, self.hourly, timezone_name=None)

        self.assertEqual(len(days), 2)
        self.assertEqual(days[0]['date'], '2026-07-18')
        self.assertEqual(len(days[0]['hourly']), 4)
        self.assertEqual(days[1]['date'], '2026-07-19')
        self.assertEqual(len(days[1]['hourly']), 2)

    def test_day_labels_use_today_for_first_day_and_weekday_after(self):
        days = OpenMeteoWeatherProvider._build_daily(self.daily, self.hourly, timezone_name=None)

        self.assertEqual(days[0]['day_label'], 'Today')
        self.assertEqual(days[1]['day_label'], 'Sun')

    def test_hourly_entries_carry_temperature_and_condition(self):
        days = OpenMeteoWeatherProvider._build_daily(self.daily, self.hourly, timezone_name=None)

        first_hour = days[0]['hourly'][0]
        self.assertEqual(first_hour['temperature'], 23.0)
        self.assertEqual(first_hour['condition_text'], 'Overcast')
        self.assertEqual(first_hour['icon'], 'fa-cloud')
        self.assertEqual(first_hour['hour_label'], '00:00')

    def test_missing_hourly_data_returns_empty_list_per_day(self):
        days = OpenMeteoWeatherProvider._build_daily(self.daily, {}, timezone_name=None)

        self.assertEqual(days[0]['hourly'], [])
        self.assertEqual(days[1]['hourly'], [])

    def test_unresolvable_timezone_skips_now_filtering_without_raising(self):
        days = OpenMeteoWeatherProvider._build_daily(self.daily, self.hourly, timezone_name='Not/AZone')

        self.assertEqual(len(days[0]['hourly']), 4)


class DescribeTests(SimpleTestCase):
    def test_known_code_resolves_to_text_and_icon(self):
        self.assertEqual(describe(95), ('Thunderstorm', 'fa-bolt'))

    def test_unknown_or_missing_code_falls_back(self):
        self.assertEqual(describe(1234), DEFAULT_CONDITION)
        self.assertEqual(describe(None), DEFAULT_CONDITION)
