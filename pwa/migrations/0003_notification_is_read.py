from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pwa', '0002_remove_endpoint_unique_constraint'),
    ]

    operations = [
        migrations.AddField(
            model_name='notification',
            name='is_read',
            field=models.BooleanField(default=False),
        ),
    ]
