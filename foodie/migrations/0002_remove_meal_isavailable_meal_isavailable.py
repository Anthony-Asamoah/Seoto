# Generated by Django 4.0.4 on 2022-05-30 20:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('foodie', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='meal',
            name='IsAvailable',
        ),
        migrations.AddField(
            model_name='meal',
            name='isAvailable',
            field=models.BooleanField(default=True),
        ),
    ]