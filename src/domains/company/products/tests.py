from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import clear_url_caches, reverse

from infrastructure.core.pagination import DefaultPagination

from . import services
from .models import Product, ProductStatus, ProductTag


class ProductApiTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.wagtail = ProductTag.objects.create(label='Wagtail', order=1)
        cls.multilingual = ProductTag.objects.create(label='Multilingual', order=2)

        cls.launched = Product.objects.create(
            title='Okodienkwan', client='Okodienkwan',
            summary='A summary.', body='The body.',
            status=ProductStatus.LAUNCHED.name, launched_on='2024-03-01',
        )
        cls.launched.tags.set([cls.wagtail, cls.multilingual])

        cls.managed = Product.objects.create(
            title='JILCE', client='JILCE',
            summary='Another summary.', body='Another body.',
            status=ProductStatus.MANAGED.name, launched_on='2023-01-01',
        )
        cls.managed.tags.set([cls.wagtail])

        cls.draft = Product.objects.create(
            title='Unfinished', client='Someone',
            summary='Not ready.', body='Not ready.',
            status=ProductStatus.DRAFT.name,
        )

    def test_slug_is_generated_from_title(self):
        self.assertEqual(self.launched.slug, 'okodienkwan')

    def test_status_choices_store_the_enum_name(self):
        """The admin form must write the same spelling the seed does — if
        choices ever store the label, admin-created products stop matching
        PUBLIC_STATUSES and silently disappear from the API."""
        stored = [choice[0] for choice in Product._meta.get_field('status').choices]
        self.assertIn('IN_PROGRESS', stored)
        self.assertNotIn('In Progress', stored)

    def test_status_is_returned_as_value_and_label(self):
        results = self.client.get(reverse('product_list')).json()['results']
        managed = next(p for p in results if p['slug'] == 'jilce')
        self.assertEqual(managed['status'], 'MANAGED')
        self.assertEqual(managed['status_display'], 'Managed')

    def test_returned_status_can_be_fed_back_into_the_filter(self):
        results = self.client.get(reverse('product_list')).json()['results']
        response = self.client.get(
            reverse('product_list'), {'status': results[0]['status']}
        )
        self.assertEqual(response.status_code, 200)

    def test_list_excludes_drafts(self):
        response = self.client.get(reverse('product_list'))
        self.assertEqual(response.status_code, 200)
        slugs = [p['slug'] for p in response.json()['results']]
        self.assertNotIn('unfinished', slugs)
        self.assertCountEqual(slugs, ['okodienkwan', 'jilce'])

    def test_list_is_paginated(self):
        body = self.client.get(reverse('product_list')).json()
        self.assertEqual(body['count'], 2)
        for key in ('count', 'next', 'previous', 'results'):
            self.assertIn(key, body)

    def test_documented_envelope_matches_the_real_one(self):
        """PaginatedProductListSerializer is hand-written, so it can drift from
        what the paginator actually returns. Catch that here."""
        from .serializers import PaginatedProductListSerializer

        body = self.client.get(reverse('product_list')).json()
        self.assertCountEqual(
            body.keys(), PaginatedProductListSerializer().fields.keys()
        )

    def test_page_size_is_capped(self):
        response = self.client.get(reverse('product_list'), {'page_size': 500})
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(
            len(response.json()['results']), settings.API_MAX_PAGE_SIZE
        )

    def test_pagination_sizes_come_from_settings(self):
        self.assertEqual(DefaultPagination.page_size, settings.API_PAGE_SIZE)
        self.assertEqual(
            DefaultPagination.max_page_size, settings.API_MAX_PAGE_SIZE
        )

    def test_list_omits_body(self):
        """The collapsed row must not ship the long-form copy."""
        results = self.client.get(reverse('product_list')).json()['results']
        self.assertNotIn('body', results[0])

    def test_multiple_tags_are_and_ed(self):
        url = reverse('product_list')
        both = self.client.get(url, {'tag': ['Wagtail', 'Multilingual']}).json()
        self.assertEqual([p['slug'] for p in both['results']], ['okodienkwan'])

        one = self.client.get(url, {'tag': ['Wagtail']}).json()
        self.assertEqual(one['count'], 2)

    def test_search_spans_client_and_copy(self):
        response = self.client.get(reverse('product_list'), {'q': 'Another'})
        self.assertEqual([p['slug'] for p in response.json()['results']], ['jilce'])

    def test_status_filter_rejects_draft(self):
        response = self.client.get(reverse('product_list'), {'status': 'DRAFT'})
        self.assertEqual(response.status_code, 400)

    def test_status_filter_accepts_public_status(self):
        response = self.client.get(reverse('product_list'), {'status': 'managed'})
        self.assertEqual([p['slug'] for p in response.json()['results']], ['jilce'])

    def test_launched_between_filters(self):
        response = self.client.get(
            reverse('product_list'), {'launched_after': '2024-01-01'}
        )
        self.assertEqual([p['slug'] for p in response.json()['results']], ['okodienkwan'])

    def test_ordering_is_whitelisted(self):
        ok = self.client.get(reverse('product_list'), {'ordering': '-launched_on'})
        self.assertEqual(
            [p['slug'] for p in ok.json()['results']], ['okodienkwan', 'jilce']
        )

        rejected = self.client.get(reverse('product_list'), {'ordering': 'client'})
        self.assertEqual(rejected.status_code, 400)

    def test_credits_are_lists_and_default_empty(self):
        self.assertEqual(self.launched.contributors, [])
        self.assertEqual(self.launched.sponsors, [])

    def test_credits_only_appear_on_the_detail_payload(self):
        self.launched.contributors = ['Ada Lovelace']
        self.launched.sponsors = ['Joint SDG Fund']
        self.launched.save()

        listed = self.client.get(reverse('product_list')).json()['results'][0]
        self.assertNotIn('contributors', listed)

        detail = self.client.get(
            reverse('product_detail', args=['okodienkwan'])
        ).json()
        self.assertEqual(detail['contributors'], ['Ada Lovelace'])
        self.assertEqual(detail['sponsors'], ['Joint SDG Fund'])

    def test_featured_sorts_first(self):
        self.managed.is_featured = True
        self.managed.save()

        results = self.client.get(reverse('product_list')).json()['results']
        self.assertEqual(results[0]['slug'], 'jilce')
        self.assertTrue(results[0]['is_featured'])

    def test_is_featured_filter(self):
        self.managed.is_featured = True
        self.managed.save()

        url = reverse('product_list')
        featured = self.client.get(url, {'is_featured': 'true'}).json()
        self.assertEqual([p['slug'] for p in featured['results']], ['jilce'])

        rest = self.client.get(url, {'is_featured': 'false'}).json()
        self.assertEqual([p['slug'] for p in rest['results']], ['okodienkwan'])

        self.assertEqual(
            self.client.get(url, {'is_featured': 'maybe'}).status_code, 400
        )

    def test_detail_returns_full_copy(self):
        response = self.client.get(
            reverse('product_detail', args=['okodienkwan'])
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['body'], 'The body.')
        self.assertCountEqual(body['tags'], ['Wagtail', 'Multilingual'])
        self.assertEqual(body['images'], [])

    def test_detail_hides_drafts(self):
        response = self.client.get(reverse('product_detail', args=['unfinished']))
        self.assertEqual(response.status_code, 404)

    def test_tags_route_is_not_shadowed_by_slug_route(self):
        response = self.client.get(reverse('product_tag_list'))
        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(response.json(), ['Wagtail', 'Multilingual'])


class ProductServiceTests(TestCase):
    """The services own the filtering, so exercise them without HTTP too."""

    @classmethod
    def setUpTestData(cls):
        cls.wagtail = ProductTag.objects.create(label='Wagtail', order=1)
        cls.multilingual = ProductTag.objects.create(label='Multilingual', order=2)

        cls.launched = Product.objects.create(
            title='Okodienkwan', summary='A summary.', body='The body.',
            status=ProductStatus.LAUNCHED.name, launched_on='2024-03-01',
        )
        cls.launched.tags.set([cls.wagtail, cls.multilingual])

        cls.draft = Product.objects.create(
            title='Unfinished', summary='Not ready.', body='Not ready.',
            status=ProductStatus.DRAFT.name,
        )
        cls.draft.tags.set([ProductTag.objects.create(label='Secret', order=3)])

    def test_published_products_excludes_drafts(self):
        self.assertNotIn(self.draft, services.published_products())

    def test_get_published_product_hides_drafts(self):
        self.assertEqual(
            services.get_published_product('okodienkwan'), self.launched
        )
        self.assertIsNone(services.get_published_product('unfinished'))

    def test_tags_are_and_ed(self):
        both = services.list_published_products(
            tags=['Wagtail', 'Multilingual']
        )
        self.assertEqual([p.slug for p in both], ['okodienkwan'])

        neither = services.list_published_products(tags=['Wagtail', 'Nope'])
        self.assertEqual(list(neither), [])

    def test_unknown_status_is_rejected(self):
        with self.assertRaises(services.ProductFilterError):
            services.list_published_products(statuses=['DRAFT'])

    def test_has_images_matches_on_absence_too(self):
        self.assertEqual(
            [p.slug for p in services.list_published_products(has_images='false')],
            ['okodienkwan'],
        )
        self.assertEqual(
            list(services.list_published_products(has_images='true')), []
        )

    def test_non_boolean_flags_are_rejected(self):
        for field in ('has_images', 'is_featured'):
            with self.subTest(field=field):
                with self.assertRaises(services.ProductFilterError) as caught:
                    services.list_published_products(**{field: 'maybe'})
                self.assertIn(field, str(caught.exception))

    def test_ordering_is_whitelisted(self):
        services.list_published_products(ordering='-launched_on')
        with self.assertRaises(services.ProductFilterError):
            services.list_published_products(ordering='client')

    def test_tag_labels_come_from_published_products_only(self):
        self.assertEqual(
            services.list_published_tag_labels(), ['Wagtail', 'Multilingual']
        )


class ApiDocsFlagTests(TestCase):
    """The docs flag is read at URLconf import time, so each case has to
    reload the URLconf rather than just flipping the setting."""

    def tearDown(self):
        clear_url_caches()

    def _get(self, path):
        with self.settings(ROOT_URLCONF='infrastructure.core.urls'):
            clear_url_caches()
            return self.client.get(path)

    @override_settings(IS_API_DOCS_ENABLED=True)
    def test_docs_served_when_enabled(self):
        import importlib
        from infrastructure.core import urls
        importlib.reload(urls)
        clear_url_caches()

        self.assertEqual(self._get('/api/').status_code, 200)
        self.assertEqual(self._get('/api/schema/').status_code, 200)

    @override_settings(IS_API_DOCS_ENABLED=False)
    def test_docs_absent_when_disabled(self):
        import importlib
        from infrastructure.core import urls
        importlib.reload(urls)
        clear_url_caches()

        self.assertEqual(self._get('/api/').status_code, 404)
        self.assertEqual(self._get('/api/schema/').status_code, 404)

    def test_products_api_still_served_with_docs_off(self):
        """The flag must gate the docs only, never the endpoints."""
        with override_settings(IS_API_DOCS_ENABLED=False):
            import importlib
            from infrastructure.core import urls
            importlib.reload(urls)
            clear_url_caches()

            self.assertEqual(self._get('/api/company/products/').status_code, 200)
