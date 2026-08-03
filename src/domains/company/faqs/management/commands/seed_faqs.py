from django.core.management.base import BaseCommand

from domains.company.faqs.models import FAQ

# Mirrors ``faqItems`` in seoto_ui (src/domains/home/data.ts). The UI has no
# sections, so these seed uncategorised; ``idx`` there is ``order`` here.
FAQS = [
    {
        'slug': 'website-product-or-custom-software',
        'order': 1,
        'question': (
            'How do I know whether I need a website, a ready-made product, or '
            'custom software?'
        ),
        'answer': (
            "That's exactly what our discovery process is for. We look at your "
            'goals, constraints, and budget first — then recommend the simplest '
            "option that fits. Often that's a website or one of our proven "
            "products; sometimes it's custom. You'll get an honest "
            'recommendation before any build begins.'
        ),
    },
    {
        'slug': 'what-does-a-project-cost',
        'order': 2,
        'question': 'What does a project cost?',
        'answer': (
            'It depends on the path. Websites and CMS projects start small; '
            'adopting a proven product (like Inventory or a single ERP module) '
            'is more affordable than custom software, which is scoped to your '
            'needs. We start with a fixed-scope discovery so you know costs up '
            "front — and we'll always point you to the right solution, not the "
            'most expensive one.'
        ),
    },
    {
        'slug': 'small-non-technical-team',
        'order': 3,
        'question': "We're a small team and not very technical — is this for us?",
        'answer': (
            'Absolutely. Most of our clients are small businesses, startups, and '
            'non-profits without an in-house tech team. We explain things in '
            'plain language, handle the technical complexity, and train your '
            'people so they can confidently run what we build.'
        ),
    },
    {
        'slug': 'how-long-does-a-project-take',
        'order': 4,
        'question': 'How long does a typical project take?',
        'answer': (
            'A website or CMS can launch in a few weeks. Adopting a proven '
            'product is faster still, since the core is already built. Custom '
            "platforms vary with scope — but you'll see working software early "
            'and often, not a long silence followed by a big reveal.'
        ),
    },
    {
        'slug': 'what-happens-after-launch',
        'order': 5,
        'question': 'What happens after launch?',
        'answer': (
            'We stay on. Monitoring, support, and training are part of how we '
            'work — so your software keeps running smoothly and your team keeps '
            'getting value from it long after go-live.'
        ),
    },
    {
        'slug': 'what-happens-on-a-consultation-call',
        'order': 6,
        'question': 'What actually happens on a consultation call?',
        'answer': (
            'A focused 30-minute conversation about your goals, challenges, and '
            "budget. No slides, no pressure. You'll leave with a clearer sense "
            'of your options — whether or not you work with us. In a hurry? You '
            'can also just call or WhatsApp us for a quick 5-minute chat.'
        ),
    },
]


class Command(BaseCommand):
    help = 'Seed the FAQs shown on the marketing site'

    def add_arguments(self, parser):
        parser.add_argument(
            '--refresh',
            action='store_true',
            help='Also update existing FAQs. Overwrites copy edited in the admin.',
        )

    def handle(self, *args, **options):
        refresh = options['refresh']
        created_count = updated_count = 0

        for entry in FAQS:
            # get_or_create by default: re-running must not clobber copy that
            # has since been edited in the admin. --refresh opts into that.
            faq, created = FAQ.objects.get_or_create(
                slug=entry['slug'], defaults=entry,
            )

            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'  Created: {faq.question}'))
            elif refresh:
                for field, value in entry.items():
                    setattr(faq, field, value)
                faq.save()
                updated_count += 1
                self.stdout.write(self.style.SUCCESS(f'  Updated: {faq.question}'))
            else:
                self.stdout.write(f'  Already exists: {faq.question}')

        self.stdout.write(self.style.SUCCESS(
            f'\nDone. {created_count} created, {updated_count} updated.'
        ))
