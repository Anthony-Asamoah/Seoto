from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse


class WeatherForecastViewTests(TestCase):
    def setUp(self):
        self.url = reverse('weather_forecast')
        cache.clear()

    @patch('home.views.weather.get_weather_provider')
    def test_gps_coordinates_skip_geolocation(self, mock_get_weather_provider):
        mock_get_weather_provider.return_value.get_forecast.return_value = {
            'temperature': 21.0,
            'feels_like': 20.0,
            'humidity': 60,
            'wind_speed': 10.0,
            'condition_code': 1,
            'condition_text': 'Mainly clear',
            'icon': 'fa-sun',
            'high': 24.0,
            'low': 15.0,
            'timezone': 'UTC',
        }

        response = self.client.get(self.url, {'lat': '5.6', 'lon': '-0.2'})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['source'], 'gps')
        self.assertEqual(data['weather']['temperature'], 21.0)
        mock_get_weather_provider.return_value.get_forecast.assert_called_once_with(5.6, -0.2)

    @patch('home.views.weather.get_weather_provider')
    @patch('home.views.weather.get_geolocation_provider')
    def test_defaults_to_ip_geolocation(self, mock_get_geo_provider, mock_get_weather_provider):
        mock_get_geo_provider.return_value.locate.return_value = {
            'lat': 5.6, 'lon': -0.2, 'city': 'Accra', 'region': 'Greater Accra', 'country': 'Ghana',
        }
        mock_get_weather_provider.return_value.get_forecast.return_value = {
            'temperature': 27.0, 'feels_like': 29.0, 'humidity': 70, 'wind_speed': 8.0,
            'condition_code': 2, 'condition_text': 'Partly cloudy', 'icon': 'fa-cloud-sun',
            'high': 30.0, 'low': 22.0, 'timezone': 'Africa/Accra',
        }

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['source'], 'ip')
        self.assertEqual(data['location']['city'], 'Accra')
        mock_get_geo_provider.return_value.locate.assert_called_once()

    @patch('home.views.weather.get_geolocation_provider')
    def test_returns_503_when_ip_cannot_be_located(self, mock_get_geo_provider):
        mock_get_geo_provider.return_value.locate.return_value = None

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 503)
        self.assertIn('error', response.json())

    @patch('home.views.weather.get_weather_provider')
    @patch('home.views.weather.get_geolocation_provider')
    def test_returns_503_when_weather_provider_fails(self, mock_get_geo_provider, mock_get_weather_provider):
        mock_get_geo_provider.return_value.locate.return_value = {
            'lat': 5.6, 'lon': -0.2, 'city': 'Accra', 'region': 'Greater Accra', 'country': 'Ghana',
        }
        mock_get_weather_provider.return_value.get_forecast.return_value = None

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 503)

    def test_invalid_coordinates_return_400(self):
        response = self.client.get(self.url, {'lat': 'not-a-number', 'lon': '-0.2'})

        self.assertEqual(response.status_code, 400)

    def test_rejects_non_get_methods(self):
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 405)
