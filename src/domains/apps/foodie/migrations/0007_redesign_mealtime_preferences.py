from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('foodie', '0006_meal_main_img_thumbnail'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # 1. Create MealTimeSlot (label is PK)
        migrations.CreateModel(
            name='MealTimeSlot',
            fields=[
                ('label', models.CharField(max_length=50, primary_key=True, serialize=False)),
                ('default_time', models.TimeField()),
            ],
        ),

        # 2. Drop the old userPreference table (boolean fields, incompatible schema)
        migrations.DeleteModel(
            name='userPreference',
        ),

        # 3. Add default_preference FK to meal
        migrations.AddField(
            model_name='meal',
            name='default_preference',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='default_meals',
                to='foodie.mealtimeslot',
            ),
        ),

        # 4. Create UserMealSchedule
        migrations.CreateModel(
            name='UserMealSchedule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('time', models.TimeField()),
                ('slot', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='user_schedules',
                    to='foodie.mealtimeslot',
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='meal_schedule',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'unique_together': {('user', 'slot')},
            },
        ),

        # 5. Re-create userPreference with slot FK (replaces boolean fields)
        migrations.CreateModel(
            name='userPreference',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('isAvailable', models.BooleanField(default=True)),
                ('meal', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='user_preferences',
                    to='foodie.meal',
                )),
                ('slot', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='preferences',
                    to='foodie.mealtimeslot',
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='meal_preferences',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'unique_together': {('user', 'meal', 'slot')},
            },
        ),
    ]
