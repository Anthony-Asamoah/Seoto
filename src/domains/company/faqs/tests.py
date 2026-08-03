from io import StringIO

from django.conf import settings
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from infrastructure.core.pagination import DefaultAPIPagination

from . import services
from .models import FAQ, FAQCategory


class FAQApiTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.billing = FAQCategory.objects.create(name='Billing', order=1)
        cls.support = FAQCategory.objects.create(name='Support', order=2)

        cls.cost = FAQ.objects.create(
            category=cls.billing,
            question='What does a project cost?',
            answer='It depends on the path.',
            order=1,
        )
        cls.launch = FAQ.objects.create(
            category=cls.support,
            question='What happens after launch?',
            answer='We stay on, monitoring and training.',
            order=1,
        )
        cls.unpublished = FAQ.objects.create(
            question='Not ready yet?',
            answer='Still being written.',
            is_published=False,
        )

    def test_slug_is_generated_from_question(self):
        self.assertEqual(self.cost.slug, 'what-does-a-project-cost')

    def test_list_excludes_unpublished(self):
        response = self.client.get(reverse('faq_list'))
        self.assertEqual(response.status_code, 200)
        slugs = [f['slug'] for f in response.json()['results']]
        self.assertNotIn('not-ready-yet', slugs)
        self.assertCountEqual(
            slugs, ['what-does-a-project-cost', 'what-happens-after-launch']
        )

    def test_list_is_paginated(self):
        body = self.client.get(reverse('faq_list')).json()
        self.assertEqual(body['count'], 2)
        for key in ('count', 'next', 'previous', 'results'):
            self.assertIn(key, body)

    def test_documented_envelope_matches_the_real_one(self):
        """PaginatedFAQListSerializer is hand-written, so it can drift from what
        the paginator actually returns. Catch that here."""
        from .serializers import PaginatedFAQListSerializer

        body = self.client.get(reverse('faq_list')).json()
        self.assertCountEqual(
            body.keys(), PaginatedFAQListSerializer().fields.keys()
        )

    def test_page_size_is_capped(self):
        response = self.client.get(reverse('faq_list'), {'page_size': 500})
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(
            len(response.json()['results']), settings.API_MAX_PAGE_SIZE
        )

    def test_pagination_sizes_come_from_settings(self):
        self.assertEqual(DefaultAPIPagination.page_size, settings.API_PAGE_SIZE)
        self.assertEqual(
            DefaultAPIPagination.max_page_size, settings.API_MAX_PAGE_SIZE
        )

    def test_list_ships_the_answer(self):
        """The accordion opens without a second request, so unlike products the
        long copy has to be on the list payload."""
        results = self.client.get(reverse('faq_list')).json()['results']
        self.assertIn('answer', results[0])
        self.assertTrue(results[0]['answer'])

    def test_category_is_returned_as_slug_and_name(self):
        results = self.client.get(reverse('faq_list')).json()['results']
        cost = next(f for f in results if f['slug'] == 'what-does-a-project-cost')
        self.assertEqual(cost['category'], 'billing')
        self.assertEqual(cost['category_name'], 'Billing')

    def test_returned_category_can_be_fed_back_into_the_filter(self):
        results = self.client.get(reverse('faq_list')).json()['results']
        response = self.client.get(
            reverse('faq_list'), {'category': results[0]['category']}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['count'], 1)

    def test_uncategorised_faqs_serialize_with_null_category(self):
        self.unpublished.is_published = True
        self.unpublished.save()

        results = self.client.get(reverse('faq_list')).json()['results']
        loose = next(f for f in results if f['slug'] == 'not-ready-yet')
        self.assertIsNone(loose['category'])
        self.assertIsNone(loose['category_name'])

    def test_multiple_categories_are_or_ed(self):
        url = reverse('faq_list')
        both = self.client.get(url, {'category': ['billing', 'support']}).json()
        self.assertEqual(both['count'], 2)

        one = self.client.get(url, {'category': ['billing']}).json()
        self.assertEqual(
            [f['slug'] for f in one['results']], ['what-does-a-project-cost']
        )

    def test_search_spans_question_and_answer(self):
        response = self.client.get(reverse('faq_list'), {'q': 'monitoring'})
        self.assertEqual(
            [f['slug'] for f in response.json()['results']],
            ['what-happens-after-launch'],
        )

    def test_ordering_is_whitelisted(self):
        ok = self.client.get(reverse('faq_list'), {'ordering': '-question'})
        self.assertEqual(
            [f['slug'] for f in ok.json()['results']],
            ['what-happens-after-launch', 'what-does-a-project-cost'],
        )

        rejected = self.client.get(reverse('faq_list'), {'ordering': 'answer'})
        self.assertEqual(rejected.status_code, 400)

    def test_featured_sorts_first_within_a_category(self):
        second = FAQ.objects.create(
            category=self.billing, question='Do you take instalments?',
            answer='Yes.', order=2, is_featured=True,
        )

        results = self.client.get(
            reverse('faq_list'), {'category': 'billing'}
        ).json()['results']
        self.assertEqual(results[0]['slug'], second.slug)

    def test_is_featured_filter(self):
        self.launch.is_featured = True
        self.launch.save()

        url = reverse('faq_list')
        featured = self.client.get(url, {'is_featured': 'true'}).json()
        self.assertEqual(
            [f['slug'] for f in featured['results']], ['what-happens-after-launch']
        )

        rest = self.client.get(url, {'is_featured': 'false'}).json()
        self.assertEqual(
            [f['slug'] for f in rest['results']], ['what-does-a-project-cost']
        )

        self.assertEqual(
            self.client.get(url, {'is_featured': 'maybe'}).status_code, 400
        )

    def test_detail_returns_the_question(self):
        response = self.client.get(
            reverse('faq_detail', args=['what-does-a-project-cost'])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['answer'], 'It depends on the path.')

    def test_detail_hides_unpublished(self):
        response = self.client.get(reverse('faq_detail', args=['not-ready-yet']))
        self.assertEqual(response.status_code, 404)

    def test_categories_route_is_not_shadowed_by_slug_route(self):
        response = self.client.get(reverse('faq_category_list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [c['slug'] for c in response.json()], ['billing', 'support']
        )


class FAQServiceTests(TestCase):
    """The services own the filtering, so exercise them without HTTP too."""

    @classmethod
    def setUpTestData(cls):
        cls.billing = FAQCategory.objects.create(name='Billing', order=1)
        cls.empty = FAQCategory.objects.create(name='Careers', order=2)

        cls.published = FAQ.objects.create(
            category=cls.billing, question='What does a project cost?',
            answer='It depends on the path.',
        )
        cls.unpublished = FAQ.objects.create(
            category=cls.empty, question='Not ready yet?',
            answer='Still being written.', is_published=False,
        )

    def test_published_faqs_excludes_unpublished(self):
        self.assertNotIn(self.unpublished, services.published_faqs())

    def test_get_published_faq_hides_unpublished(self):
        self.assertEqual(
            services.get_published_faq('what-does-a-project-cost'), self.published
        )
        self.assertIsNone(services.get_published_faq('not-ready-yet'))

    def test_categories_are_or_ed(self):
        both = services.list_published_faqs(categories=['billing', 'careers'])
        self.assertEqual([f.slug for f in both], ['what-does-a-project-cost'])

        neither = services.list_published_faqs(categories=['nope'])
        self.assertEqual(list(neither), [])

    def test_non_boolean_flags_are_rejected(self):
        with self.assertRaises(services.FAQFilterError) as caught:
            services.list_published_faqs(is_featured='maybe')
        self.assertIn('is_featured', str(caught.exception))

    def test_ordering_is_whitelisted(self):
        services.list_published_faqs(ordering='-updated_at')
        with self.assertRaises(services.FAQFilterError):
            services.list_published_faqs(ordering='answer')

    def test_empty_categories_are_dropped(self):
        """A section whose only question is unpublished would otherwise render
        as a heading with nothing under it."""
        self.assertEqual(
            [c.slug for c in services.list_published_categories()], ['billing']
        )

    def test_schema_faqs_respects_the_opt_out(self):
        self.assertIn(self.published, services.schema_faqs())

        self.published.include_in_schema = False
        self.published.save()
        self.assertEqual(list(services.schema_faqs()), [])


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
