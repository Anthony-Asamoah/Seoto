# Generated by Django 4.0.4 on 2022-06-17 09:21

import datetime
from django.db import migrations, models
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('jotter', '0012_todo_added_on_tracker_added_on_tracker_completed_on_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='todo',
            name='added_on',
            field=models.DateTimeField(default=datetime.datetime(2022, 6, 17, 9, 21, 43, 626390, tzinfo=utc)),
        ),
        migrations.AlterField(
            model_name='tracker',
            name='added_on',
            field=models.DateTimeField(default=datetime.datetime(2022, 6, 17, 9, 21, 43, 625390, tzinfo=utc)),
        ),
    ]