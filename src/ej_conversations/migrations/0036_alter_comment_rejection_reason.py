# Generated by Django 4.2 on 2024-09-30 19:34

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ej_conversations", "0035_merge_20240917_1036"),
    ]

    operations = [
        migrations.AlterField(
            model_name="comment",
            name="rejection_reason",
            field=models.IntegerField(
                choices=[
                    (0, "User provided"),
                    (10, "Incomplete or incomprehensible text"),
                    (20, "Off-topic"),
                    (30, "Offensive content or language"),
                    (40, "Duplicated content"),
                    (50, "Violates terms of service of the platform"),
                ],
                default=0,
            ),
        ),
    ]
