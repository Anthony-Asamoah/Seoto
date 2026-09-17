from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse


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
