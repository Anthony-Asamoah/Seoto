import json
from pathlib import Path

from django.contrib.auth.management import create_permissions
from django.db import migrations

FIXTURE = Path(__file__).resolve().parents[1] / 'fixtures' / 'groups.json'


def load_groups():
    return [entry['fields'] for entry in json.loads(FIXTURE.read_text())]


def seed_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    groups = load_groups()

    labels = {perm[1] for group in groups for perm in group['permissions']}
    for label in labels:
        app_config = apps.get_app_config(label)
        app_config.models_module = True
        create_permissions(app_config, apps=apps, verbosity=0)
        app_config.models_module = None

    for fields in groups:
        group, _ = Group.objects.get_or_create(name=fields['name'])
        group.permissions.set([
            Permission.objects.get(
                codename=codename, content_type__app_label=app_label, content_type__model=model,
            )
            for codename, app_label, model in fields['permissions']
        ])


def unseed_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name__in=[fields['name'] for fields in load_groups()]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0010_alter_user_profile_options'),
        ('auth', '0012_alter_user_first_name_max_length'),
        ('contenttypes', '0002_remove_content_type_name'),
        ('blog', '0007_alter_post_options_alter_postcomment_options_and_more'),
        ('foodie', '0012_alter_dailymealsuggestion_options_alter_meal_options_and_more'),
        ('jotter', '0003_alter_todo_options_alter_tracker_options'),
        ('rhymes', '0003_alter_rhyme_options'),
        ('spending_tracker', '0015_alter_account_options_alter_category_options_and_more'),
        ('pwa', '0004_alter_notification_options_and_more'),
        ('theme', '0002_alter_themepreset_options_alter_themerating_options_and_more'),
        ('home', '0003_scheduledjobrun'),
        ('website_products', '0003_alter_product_options_product_contributors_and_more'),
        ('website_faqs', '0001_initial'),
        ('company_staff', '0006_close_superseded_assignments'),
    ]

    operations = [
        migrations.RunPython(seed_groups, unseed_groups),
    ]
