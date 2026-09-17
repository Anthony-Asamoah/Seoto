from django.test import TestCase

from domains.company.faqs import services
from domains.company.faqs.models import FAQ, FAQCategory


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
