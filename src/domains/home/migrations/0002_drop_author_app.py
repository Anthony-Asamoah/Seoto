from django.db import migrations

# The `author` app was removed, so its own migrations can no longer run the drop.
# Ordered children-first; the migration history and content types go too, otherwise
# Django replays `author` on a fresh clone and re-creates the tables.
TABLES = (
    'author_introlinks',
    'author_intro',
    'author_education',
    'author_jobexperience',
    'author_hobby',
    'author_stack',
    'author_message',
)


def drop_author_tables(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        for table in TABLES:
            cursor.execute(f'DROP TABLE IF EXISTS "{table}"')
        cursor.execute("DELETE FROM django_migrations WHERE app = 'author'")

    ContentType = apps.get_model('contenttypes', 'ContentType')
    Permission = apps.get_model('auth', 'Permission')
    content_types = ContentType.objects.filter(app_label='author')
    Permission.objects.filter(content_type__in=content_types).delete()
    content_types.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0001_initial'),
        ('contenttypes', '0002_remove_content_type_name'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(drop_author_tables, migrations.RunPython.noop),
    ]
