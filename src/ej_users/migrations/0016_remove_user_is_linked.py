# Generated by Django 4.1.13 on 2024-08-29 20:24

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("ej_users", "0015_user_has_completed_registration"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="user",
            name="is_linked",
        ),
    ]
