from django.db import migrations

POSITIONS = [
    ('Principal', 'Owner of the business. Sets direction, signs the work, carries the risk.'),
    ('Engineering Lead', 'Owns technical direction and review across projects.'),
    ('Software Engineer', 'Builds and maintains client and in-house software.'),
    ('Frontend Engineer', 'Interfaces, templates and client-side behaviour.'),
    ('Backend Engineer', 'Services, data models and integrations.'),
    ('Mobile Engineer', 'Android and iOS delivery.'),
    ('DevOps Engineer', 'Deployment, hosting, monitoring and backups.'),
    ('QA Engineer', 'Test plans, regression passes and release sign-off.'),
    ('Product Designer', 'Research, wireframes, UI design and design systems.'),
    ('Data Analyst', 'Reporting, dashboards and data cleanup for clients.'),
    ('Project Manager', 'Scope, schedule and the client relationship during delivery.'),
    ('Business Development Officer', 'Leads, proposals and pricing.'),
    ('Marketing Officer', 'Content, social and the marketing site.'),
    ('Finance & Admin Officer', 'Invoicing, payroll, filings and procurement.'),
    ('Support Officer', 'First line for client issues and maintenance requests.'),
    ('Intern', 'Supervised placement on live work.'),
    ('Contractor', 'Engaged per project rather than employed.'),
]

TEAMS = [
    ('Engineering', 'Everyone who writes or ships code.'),
    ('Design', 'Product and brand design.'),
    ('Delivery', 'Project management, QA and client communication.'),
    ('Growth', 'Business development and marketing.'),
    ('Operations', 'Finance, admin and support.'),
]


def seed(apps, schema_editor):
    Position = apps.get_model('company_staff', 'Position')
    Team = apps.get_model('company_staff', 'Team')

    for name, description in POSITIONS:
        Position.objects.get_or_create(name=name, defaults={'description': description})

    for name, description in TEAMS:
        Team.objects.get_or_create(name=name, defaults={'description': description})


def unseed(apps, schema_editor):
    # Only the seeded rows, and only while nothing points at them.
    Position = apps.get_model('company_staff', 'Position')
    Team = apps.get_model('company_staff', 'Team')

    Position.objects.filter(
        name__in=[name for name, _ in POSITIONS], assignments__isnull=True
    ).delete()
    Team.objects.filter(
        name__in=[name for name, _ in TEAMS], memberships__isnull=True
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('company_staff', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
