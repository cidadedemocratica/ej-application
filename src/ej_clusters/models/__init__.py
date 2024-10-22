from .clusterization import Clusterization
from .cluster import Cluster
from .stereotype import Stereotype
from .stereotype_vote import StereotypeVote

#
# Patch conversation app keeping namespace clean.
#
def apply_patch(f):
    return f()


@apply_patch
def _patch_conversation_app():
    from ej.components import register_menu
    from ej_conversations.models import Conversation
    from django.utils.translation import gettext as _
    from sidekick import delegate_to, lazy
    from hyperpython import a

    not_given = object()

    def get_clusterization(conversation, default=not_given):
        """
        Initialize a clusterization object for the given conversation, if it does
        not exist.
        """
        try:
            return conversation.clusterization
        except (AttributeError, Clusterization.DoesNotExist):
            if default is not_given:
                mgm, _ = Clusterization.objects.get_or_create(conversation=conversation)
                return mgm
            else:
                return default

    Conversation.get_clusterization = get_clusterization
    Conversation._clusterization = lazy(get_clusterization)
    Conversation.clusters = delegate_to("_clusterization")
