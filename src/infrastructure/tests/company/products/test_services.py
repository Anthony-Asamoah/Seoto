from django.test import TestCase

from domains.company.products import services
from domains.company.products.models import Product, ProductStatus, ProductTag


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
