from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from domains.company.faqs.models import FAQ


class SeedFAQsTests(TestCase):

    def seed(self, *args):
        call_command('seed_faqs', *args, stdout=StringIO())

    def test_seed_is_idempotent_and_serves(self):
        self.seed()
        self.seed()

        self.assertEqual(FAQ.objects.count(), 6)
        body = self.client.get(reverse('faq_list')).json()
        self.assertEqual(body['count'], 6)
        self.assertEqual(
            [f['slug'] for f in body['results']][0],
            'website-product-or-custom-software',
        )

    def test_refresh_restores_edited_copy(self):
        self.seed()
        faq = FAQ.objects.get(slug='what-does-a-project-cost')
        faq.answer = 'Edited in the admin.'
        faq.save()

        self.seed()
        faq.refresh_from_db()
        self.assertEqual(faq.answer, 'Edited in the admin.')

        self.seed('--refresh')
        faq.refresh_from_db()
        self.assertNotEqual(faq.answer, 'Edited in the admin.')
