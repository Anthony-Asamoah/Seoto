# Generated by Django 4.0.4 on 2022-06-03 13:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jotter', '0007_alter_todo_priority'),
    ]

    operations = [
        migrations.AlterField(
            model_name='todo',
            name='priority',
            field=models.CharField(choices=[('High', 'High'), ('Medium', 'Medium'), ('Low', 'Low')], default='Low', max_length=10),
        ),
    ]