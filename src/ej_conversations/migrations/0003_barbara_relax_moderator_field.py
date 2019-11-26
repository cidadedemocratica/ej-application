# Generated by Django 2.2.3 on 2019-07-28 02:09

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [("ej_conversations", "0002_barbara_rc1")]

    operations = [
        migrations.AlterModelOptions(
            name="conversation",
            options={
                "ordering": ["created"],
                "permissions": (
                    ("can_publish_promoted", "Can publish promoted conversations"),
                    ("is_moderator", "Can moderate comments in any conversation"),
                ),
                "verbose_name": "Conversation",
                "verbose_name_plural": "Conversations",
            },
        ),
        migrations.AlterField(
            model_name="comment",
            name="moderator",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="moderated_comments",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
