# Generated by Django 4.0.4 on 2022-06-06 19:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jotter', '0010_remove_todo_description'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tracker',
            name='timestamp',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
    ]
