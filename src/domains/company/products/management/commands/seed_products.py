from django.core.management.base import BaseCommand

from domains.company.products.models import Product, ProductStatus, ProductTag

PRODUCTS = [
    {
        'slug': 'pelben-pharmacy',
        'title': 'PelBen Pharmacy',
        'client': 'PelBen Pharmacy',
        'live_url': 'https://pelbenpharmacy.com',
        'status': ProductStatus.IN_PROGRESS.name,
        'order': 1,
        'summary': 'A website for a community pharmacy in Teshie Nungua, Accra.',
        'body': (
            'PelBen Pharmacy is a community pharmacy built around the patient, '
            'offering more than dispensing: prescription management, health '
            'consultations, on-site screenings for blood pressure, glucose and '
            'cholesterol, vaccinations, medication therapy reviews and chronic '
            'disease monitoring. The site presents those services alongside '
            'opening hours and location so patients can find what they need '
            'before they visit.'
        ),
        'tags': ['CMS'],
        'is_featured': False,
        'contributors': [],
        'sponsors': [],
    },
    {
        'slug': 'okodienkwan',
        'title': 'Ɔkɔdeɛ Nkwan',
        'client': 'Ɔkɔdeɛ Nkwan',
        'live_url': 'https://okodienkwan.com',
        'status': ProductStatus.LAUNCHED.name,
        'order': 2,
        'summary': 'A site for a Ghanaian chop bar with two branches in Abelemkpe, Accra.',
        'body': (
            'Ɔkɔdeɛ Nkwan is an authentic Ghanaian chop bar founded by Charity '
            'Appiah — a welcoming space for comfort, good food and community. '
            'The site carries the full menu of staples, soups and proteins '
            'with prices, covers both Swaniker Street branches with their '
            'hours, and opens a route to catering and bulk orders.'
        ),
        'tags': ['CMS'],
        'is_featured': True,
        'contributors': [],
        'sponsors': [],
    },
    {
        'slug': 'msme-gateway',
        'title': 'Ghana MSME Gateway',
        'client': 'Ghana Enterprises Agency',
        'live_url': 'https://msmegateway.com',
        'status': ProductStatus.LAUNCHED.name,
        'order': 3,
        'summary': (
            'The Ghana Enterprises Agency’s official multivendor marketplace '
            'for micro, small and medium enterprises.'
        ),
        'body': (
            'MSME Gateway is a digital platform helping Ghanaian MSMEs start, '
            'grow and scale, bringing formalisation guidance, regulatory '
            'information, digital skills resources and market access into one '
            'entry point. It runs an e-commerce marketplace connecting vendors '
            'across all 16 regions with buyers, onboards vendors in under 48 '
            'hours with no listing fees, and handles buyer protection and '
            'payment processing. Delivered with UNCTAD, UNCDF, UNDP and the '
            'Ghana Enterprises Agency, with EU support through the Joint SDG Fund.'
        ),
        'tags': ['KACE'],
        'is_featured': False,
        'contributors': ['GI-KACE TEAM'],
        'sponsors': ['UNDP', 'GEA'],
    },
    {
        'slug': 'emi-dare',
        'title': 'EMI',
        'client': 'GI-KACE',
        'live_url': 'https://emi.dare.org.gh/',
        'status': ProductStatus.LAUNCHED.name,
        'order': 4,
        'summary': 'A marketplace for products and professional services across Africa.',
        'body': (
            'EMI is a marketplace for discovering, connecting and trading with '
            'confidence — listing both products and professional services from '
            'verified Ghanaian vendors. Beyond ordinary listings it supports '
            'bulk purchase requests that aggregators bid on competitively, '
            'along with seller verification, order management and secure '
            'payments.'
        ),
        'tags': ['KACE'],
        'is_featured': False,
        'contributors': ['GI-KACE TEAM'],
        'sponsors': ['MasterCard Foundation'],
    },
]


class Command(BaseCommand):
    help = 'Seed the products shown on the marketing site'

    def add_arguments(self, parser):
        parser.add_argument(
            '--refresh',
            action='store_true',
            help='Also update existing products. Overwrites copy edited in the admin.',
        )

    def handle(self, *args, **options):
        refresh = options['refresh']
        created_count = updated_count = 0

        for entry in PRODUCTS:
            entry = dict(entry)
            tag_labels = entry.pop('tags', [])

            # get_or_create by default: re-running must not clobber copy that
            # has since been edited in the admin. --refresh opts into that.
            product, created = Product.objects.get_or_create(
                slug=entry['slug'], defaults=entry,
            )

            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'  Created: {product.title}'))
            elif refresh:
                for field, value in entry.items():
                    setattr(product, field, value)
                product.save()
                updated_count += 1
                self.stdout.write(self.style.SUCCESS(f'  Updated: {product.title}'))
            else:
                self.stdout.write(f'  Already exists: {product.title}')
                continue

            tags = [
                ProductTag.objects.get_or_create(label=label)[0]
                for label in tag_labels
            ]
            product.tags.set(tags)

        self.stdout.write(self.style.SUCCESS(
            f'\nDone. {created_count} created, {updated_count} updated.'
        ))
