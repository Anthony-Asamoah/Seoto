from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import RequestFactory, TestCase
from django.urls import NoReverseMatch, reverse
from django_otp.plugins.otp_totp.models import TOTPDevice

from common.admin import sidebar_navigation
from domains.consultations.models import ConsultationBooking, ConsultationRequest
from infrastructure.tests.accounts.helpers import current_token


class ConsultationAdminTests(TestCase):

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_superuser('root', 'root@example.com', 'pw-pw-pw-pw')
        device = TOTPDevice.objects.create(user=self.user, name='Authenticator', confirmed=True)
        self.client.post(
            reverse('admin:login'),
            {'username': 'root', 'password': 'pw-pw-pw-pw', 'otp_token': current_token(device)},
        )
        self.consultation = ConsultationRequest.objects.create(
            kind='full', name='Ama', email='ama@example.com', message='Hello',
        )
        ConsultationBooking.objects.create(
            consultation=self.consultation, scheduling_url='https://calendly.com/x',
        )

    def test_pages_render(self):
        urls = [
            reverse('admin:consultations_consultationrequest_changelist'),
            reverse('admin:consultations_consultationrequest_change', args=[self.consultation.pk]),
            reverse('admin:consultations_consultationbooking_changelist'),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_change_page_is_read_only(self):
        response = self.client.get(
            reverse('admin:consultations_consultationrequest_change', args=[self.consultation.pk])
        )

        self.assertContains(response, 'ama@example.com')
        self.assertNotContains(response, 'name="email"')
        self.assertNotContains(response, 'name="booking-0-event_uri"')

    def test_add_is_refused(self):
        response = self.client.get(reverse('admin:consultations_consultationrequest_add'))
        self.assertEqual(response.status_code, 403)

    def test_edits_are_refused(self):
        self.client.post(
            reverse('admin:consultations_consultationrequest_change', args=[self.consultation.pk]),
            {'name': 'Changed'},
        )
        self.consultation.refresh_from_db()
        self.assertEqual(self.consultation.name, 'Ama')


class ConsultationSidebarTests(TestCase):

    def test_consultations_sit_in_the_website_section(self):
        request = RequestFactory().get('/admin/')
        request.user = User.objects.create_superuser('root', 'root@example.com', 'pw-pw-pw-pw')

        website = next(group for group in sidebar_navigation(request) if group['title'] == 'Website')

        item = next(item for item in website['items'] if item['title'] == 'Consultations')
        self.assertEqual(
            {link['link'] for link in item['items']},
            {
                reverse('admin:consultations_consultationrequest_changelist'),
                reverse('admin:consultations_consultationbooking_changelist'),
            },
        )
