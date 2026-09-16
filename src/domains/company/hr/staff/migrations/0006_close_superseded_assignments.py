from datetime import timedelta

from django.db import migrations


def close_superseded(apps, schema_editor):
    """rows used to supersede each other per member; give each an explicit end"""
    Assignment = apps.get_model('company_staff', 'Assignment')
    rows = Assignment.objects.order_by('member_id', 'effective_from', 'id')
    previous = None
    for row in rows:
        if previous and previous.member_id == row.member_id and previous.effective_to is None:
            previous.effective_to = row.effective_from - timedelta(days=1)
            if previous.effective_to >= previous.effective_from:
                previous.save(update_fields=['effective_to'])
        previous = row


class Migration(migrations.Migration):
    dependencies = [
        ('company_staff', '0005_remove_assignment_unique_member_assignment_date_and_more'),
    ]

    operations = [
        migrations.RunPython(close_superseded, migrations.RunPython.noop),
    ]
