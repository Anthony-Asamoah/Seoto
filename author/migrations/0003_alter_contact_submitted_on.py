# Generated by Django 4.0.4 on 2022-06-17 09:21

import datetime
from django.db import migrations, models
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('author', '0002_contact_replied_contact_submitted_on'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contact',
            name='submitted_on',
            field=models.DateTimeField(default=datetime.datetime(2022, 6, 17, 9, 21, 43, 537385, tzinfo=utc)),
        ),
    ]