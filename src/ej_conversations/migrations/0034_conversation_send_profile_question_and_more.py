# Generated by Django 4.1.13 on 2024-08-17 15:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ej_conversations", "0033_conversation_participants_can_add_comments"),
    ]

    operations = [
        migrations.AddField(
            model_name="conversation",
            name="send_profile_question",
            field=models.BooleanField(
                default=False,
                help_text="Send a question to participants to complete their profile.",
                verbose_name="Send profile question?",
            ),
        ),
        migrations.AddField(
            model_name="conversation",
            name="votes_to_send_profile_question",
            field=models.IntegerField(
                default=0,
                help_text="Number of votes to send profile question.",
                verbose_name="Votes to send profile question",
            ),
        ),
    ]
