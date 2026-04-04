import sys

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import IntegrityError

from ej_conversations.models import Conversation
from ...factories import cluster_votes, make_conversation_with_clusters

User = get_user_model()


class Command(BaseCommand):
    help = "Create synthetic conversation clusters"

    def add_arguments(self, parser):
        parser.add_argument(
            "--silent", action="store_true", help="Prevents showing debug info"
        )
        parser.add_argument(
            "--force",
            "-f",
            action="store_true",
            help="Force recreation of clusters",
        )

    def handle(self, *args, silent=False, force=False, **options):
        if force:
            Conversation.objects.filter(title="Economy").delete()
            Conversation.objects.filter(title="Educação").delete()
        try:
            conversation = make_conversation_with_clusters()
        except IntegrityError:
            print(
                "ERROR: Could not create clusterization because the sample "
                "conversation already exists.\n"
                "Try executing with -f to delete a previously created sample "
                "conversation.",
                file=sys.stderr,
            )
        else:
            cluster_votes(conversation, User.objects.all())
