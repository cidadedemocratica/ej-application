# Generated by Django 2.0.6 on 2018-07-04 18:07

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ej_missions', '0022_mission_created_at'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mission',
            name='users',
            field=models.ManyToManyField(blank=True, to=settings.AUTH_USER_MODEL),
        ),
    ]
