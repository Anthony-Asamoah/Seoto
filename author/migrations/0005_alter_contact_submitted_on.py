# Generated by Django 4.0.4 on 2022-06-17 10:02

import datetime
from django.db import migrations, models
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('author', '0004_alter_contact_submitted_on'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contact',
            name='submitted_on',
            field=models.DateTimeField(default=datetime.datetime(2022, 6, 17, 10, 2, 13, 569137, tzinfo=utc)),
        ),
    ]
