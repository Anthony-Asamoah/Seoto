# Generated by Django 4.0.4 on 2022-06-17 10:11

import datetime
from django.db import migrations, models
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('jotter', '0016_alter_todo_added_on_alter_tracker_added_on'),
    ]

    operations = [
        migrations.AlterField(
            model_name='todo',
            name='added_on',
            field=models.DateTimeField(default=datetime.datetime(2022, 6, 17, 10, 11, 31, 185730, tzinfo=utc)),
        ),
        migrations.AlterField(
            model_name='tracker',
            name='added_on',
            field=models.DateTimeField(default=datetime.datetime(2022, 6, 17, 10, 11, 31, 184729, tzinfo=utc)),
        ),
    ]