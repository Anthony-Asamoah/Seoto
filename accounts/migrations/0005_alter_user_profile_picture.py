# Generated by Django 4.0.4 on 2022-06-22 15:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_user_profile_contact'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user_profile',
            name='picture',
            field=models.ImageField(default='../seoto/static/img/profile_pic.png', upload_to='accounts/%Y-%m-%d'),
        ),
    ]