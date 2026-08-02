from unittest.mock import patch

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse


class WeatherForecastViewTests(TestCase):
    def setUp(self):
        self.url = reverse('weather_forecast')
        cache.clear()

    @patch('domains.home.views.weather.get_weather_provider')
    @patch('domains.home.views.weather.get_geolocation_provider')
    def test_gps_coordinates_skip_ip_lookup_but_reverse_geocode(self, mock_get_geo_provider, mock_get_weather_provider):
        mock_get_geo_provider.return_value.reverse.return_value = {
            'city': 'Accra', 'region': 'Greater Accra', 'country': 'Ghana',
        }
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
            'daily': [
                {'date': '2026-07-18', 'day_label': 'Today', 'high': 24.0, 'low': 15.0,
                 'condition_text': 'Mainly clear', 'icon': 'fa-sun'},
            ],
        }

        response = self.client.get(self.url, {'lat': '5.6', 'lon': '-0.2'})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['source'], 'gps')
        self.assertEqual(data['weather']['temperature'], 21.0)
        self.assertEqual(data['location']['city'], 'Accra')
        self.assertEqual(len(data['weather']['daily']), 1)
        mock_get_weather_provider.return_value.get_forecast.assert_called_once_with(5.6, -0.2)
        mock_get_geo_provider.return_value.reverse.assert_called_once_with(5.6, -0.2)
        mock_get_geo_provider.return_value.locate.assert_not_called()

    @patch('domains.home.views.weather.get_weather_provider')
    @patch('domains.home.views.weather.get_geolocation_provider')
    def test_gps_reverse_geocode_failure_still_returns_weather(self, mock_get_geo_provider, mock_get_weather_provider):
        mock_get_geo_provider.return_value.reverse.return_value = None
        mock_get_weather_provider.return_value.get_forecast.return_value = {
            'temperature': 21.0, 'feels_like': 20.0, 'humidity': 60, 'wind_speed': 10.0,
            'condition_code': 1, 'condition_text': 'Mainly clear', 'icon': 'fa-sun',
            'high': 24.0, 'low': 15.0, 'timezone': 'UTC', 'daily': [],
        }

        response = self.client.get(self.url, {'lat': '5.6', 'lon': '-0.2'})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['location']['city'], '')

    @patch('domains.home.views.weather.get_weather_provider')
    @patch('domains.home.views.weather.get_geolocation_provider')
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

    @patch('domains.home.views.weather.get_geolocation_provider')
    def test_returns_503_when_ip_cannot_be_located(self, mock_get_geo_provider):
        mock_get_geo_provider.return_value.locate.return_value = None

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 503)
        self.assertIn('error', response.json())

    @patch('domains.home.views.weather.get_weather_provider')
    @patch('domains.home.views.weather.get_geolocation_provider')
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

    @patch('domains.home.views.weather.get_weather_provider')
    @patch('domains.home.views.weather.get_geolocation_provider')
    def test_searched_location_uses_supplied_label_without_reverse_geocode(self, mock_get_geo_provider, mock_get_weather_provider):
        mock_get_weather_provider.return_value.get_forecast.return_value = {
            'temperature': 12.0, 'feels_like': 10.0, 'humidity': 80, 'wind_speed': 15.0,
            'condition_code': 3, 'condition_text': 'Overcast', 'icon': 'fa-cloud',
            'high': 14.0, 'low': 8.0, 'timezone': 'Europe/London', 'daily': [],
        }

        response = self.client.get(self.url, {
            'lat': '51.5', 'lon': '-0.12', 'source': 'search',
            'city': 'London', 'region': 'England', 'country': 'United Kingdom',
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['source'], 'search')
        self.assertEqual(data['location']['city'], 'London')
        self.assertEqual(data['location']['country'], 'United Kingdom')
        mock_get_weather_provider.return_value.get_forecast.assert_called_once_with(51.5, -0.12)
        mock_get_geo_provider.return_value.reverse.assert_not_called()


class WeatherSearchViewTests(TestCase):
    def setUp(self):
        self.url = reverse('weather_search')
        cache.clear()

    @patch('domains.home.views.weather.get_geolocation_provider')
    def test_returns_matching_places(self, mock_get_geo_provider):
        mock_get_geo_provider.return_value.search.return_value = [
            {'city': 'London', 'region': 'England', 'country': 'United Kingdom', 'lat': 51.5, 'lon': -0.12},
            {'city': 'London', 'region': 'Ontario', 'country': 'Canada', 'lat': 42.98, 'lon': -81.25},
        ]

        response = self.client.get(self.url, {'q': 'London'})

        self.assertEqual(response.status_code, 200)
        results = response.json()['results']
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['country'], 'United Kingdom')
        mock_get_geo_provider.return_value.search.assert_called_once_with('London')

    @patch('domains.home.views.weather.get_geolocation_provider')
    def test_short_query_skips_provider(self, mock_get_geo_provider):
        response = self.client.get(self.url, {'q': 'L'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['results'], [])
        mock_get_geo_provider.return_value.search.assert_not_called()

    @patch('domains.home.views.weather.get_geolocation_provider')
    def test_second_identical_query_is_served_from_cache(self, mock_get_geo_provider):
        mock_get_geo_provider.return_value.search.return_value = [
            {'city': 'Paris', 'region': 'Île-de-France', 'country': 'France', 'lat': 48.85, 'lon': 2.35},
        ]

        self.client.get(self.url, {'q': 'Paris'})
        self.client.get(self.url, {'q': 'paris'})  # case-insensitive cache key

        self.assertEqual(mock_get_geo_provider.return_value.search.call_count, 1)

    def test_rejects_non_get_methods(self):
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 405)


@override_settings(
    SECURE_SSL_REDIRECT=False,
    # The 403 page extends base.html, whose {% static %} tags would otherwise need a
    # collectstatic manifest to resolve.
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    },
)
class CsrfFailureViewTests(TestCase):
    """
    The POSTs here deliberately carry no CSRF token, so CsrfViewMiddleware rejects
    them and hands off to home.views.error_handlers.csrf_failure.
    """

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.url = reverse('logout')
        self.same_origin = {'HTTP_REFERER': 'http://testserver/spending_tracker/'}

    def test_rejected_post_gets_retry_page_with_fresh_token(self):
        response = self.client.post(self.url, {'note': 'lunch money'}, **self.same_origin)

        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, 'Home/403_csrf.html')
        self.assertContains(response, 'Try Again', status_code=403)
        self.assertContains(response, 'name="note" value="lunch money"', status_code=403)
        self.assertTrue(response.cookies['csrftoken'].value)

    def test_retry_form_posts_back_to_the_original_path(self):
        response = self.client.post(f'{self.url}?next=/blog/', {}, **self.same_origin)

        self.assertContains(response, f'action="{self.url}?next=/blog/"', status_code=403)

    def test_submitted_values_are_escaped(self):
        response = self.client.post(
            self.url, {'note': '"><script>alert(1)</script>'}, **self.same_origin
        )

        self.assertNotContains(response, '<script>alert(1)</script>', status_code=403)

    def test_sensitive_fields_are_not_replayed(self):
        response = self.client.post(
            self.url,
            {'username': 'tony', 'password': 'hunter2'},
            **self.same_origin,
        )

        self.assertNotContains(response, 'hunter2', status_code=403)
        self.assertNotContains(response, 'Try Again', status_code=403)
        self.assertContains(response, 'password', status_code=403)

    def test_cross_origin_post_is_not_offered_a_retry(self):
        response = self.client.post(
            self.url, {'note': 'lunch money'}, HTTP_REFERER='https://evil.example/attack'
        )

        self.assertEqual(response.status_code, 403)
        self.assertNotContains(response, 'Try Again', status_code=403)
        self.assertNotContains(response, 'lunch money', status_code=403)

    def test_post_without_referer_or_origin_is_not_offered_a_retry(self):
        response = self.client.post(self.url, {'note': 'lunch money'})

        self.assertNotContains(response, 'Try Again', status_code=403)

    def test_file_upload_is_not_offered_a_retry(self):
        upload = SimpleUploadedFile('receipt.txt', b'receipt', content_type='text/plain')

        response = self.client.post(
            self.url, {'note': 'lunch money', 'receipt': upload}, **self.same_origin
        )

        self.assertNotContains(response, 'Try Again', status_code=403)

    def test_ajax_request_gets_json_so_the_client_can_retry(self):
        response = self.client.post(
            self.url,
            {'note': 'lunch money'},
            HTTP_ACCEPT='application/json',
            **self.same_origin,
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error'], 'csrf_failure')
        self.assertTrue(response.cookies['csrftoken'].value)

    def test_valid_token_still_passes_through(self):
        client = Client(enforce_csrf_checks=True)
        client.get(reverse('login'))  # seeds the CSRF cookie
        token = client.cookies['csrftoken'].value

        response = client.post(self.url, {'csrfmiddlewaretoken': token}, **self.same_origin)

        self.assertNotEqual(response.status_code, 403)
