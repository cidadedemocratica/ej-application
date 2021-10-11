# Generated by Django 2.2.19 on 2021-08-02 20:39

from django.db import migrations
from django.utils.text import slugify
from django.db import transaction
from django.utils.translation import ugettext_lazy as _


def set_board_on_conversation(apps, schema_editor):
    db_alias = schema_editor.connection.alias
    Conversation = apps.get_model("ej_conversations", "Conversation")

    for conversation in Conversation.objects.all():
        try:
            with transaction.atomic():
                for board in conversation.boards.all():
                    conversation.board = board
                    conversation.save()
        except Exception as e:
            print(e)


class Migration(migrations.Migration):

    dependencies = [
        ("ej_boards", "0003_create_default_board"),
    ]

    operations = [migrations.RunPython(set_board_on_conversation)]
