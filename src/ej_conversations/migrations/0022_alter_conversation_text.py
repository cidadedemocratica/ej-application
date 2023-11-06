# Generated by Django 3.2 on 2023-11-06 15:48

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ej_conversations", "0021_auto_20230922_1408"),
    ]

    operations = [
        migrations.AlterField(
            model_name="conversation",
            name="text",
            field=models.TextField(
                help_text="What do you want to know about participants? The conversation question will be the starting point for collecting opinions. ",
                verbose_name="Question",
            ),
        ),
    ]
