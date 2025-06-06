# Generated by Django 5.0 on 2023-12-25 14:22

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='todo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('priority', models.CharField(choices=[('High', 'High'), ('Medium', 'Medium'), ('Low', 'Low')], default='Low', max_length=10)),
                ('notes', models.TextField(blank=True, null=True)),
                ('reminder', models.DateTimeField(blank=True, null=True)),
                ('isCompleted', models.BooleanField(default=False)),
                ('completed_on', models.DateTimeField(blank=True, null=True)),
                ('added_on', models.DateTimeField(default=django.utils.timezone.now)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'todo',
            },
        ),
        migrations.CreateModel(
            name='tracker',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category', models.CharField(choices=[('Anime', 'Anime'), ('Movie', 'Movie'), ('Series', 'Series'), ('Book', 'Book'), ('Manga', 'Manga'), ('Webtoon', 'Webtoon'), ('Other', 'Other')], default='Other', max_length=10)),
                ('title', models.CharField(max_length=100)),
                ('episode', models.IntegerField(blank=True, null=True)),
                ('chapter', models.IntegerField(blank=True, null=True)),
                ('timestamp', models.CharField(blank=True, max_length=20, null=True)),
                ('link', models.URLField(blank=True, null=True)),
                ('added_on', models.DateTimeField(default=django.utils.timezone.now)),
                ('isCompleted', models.BooleanField(default=False)),
                ('completed_on', models.DateTimeField(blank=True, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'tracker',
            },
        ),
    ]
