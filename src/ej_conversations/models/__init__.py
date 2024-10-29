from logging import getLogger

from .comment import Comment
from .comment_queryset import CommentQuerySet
from .conversation import Conversation, ConversationTag
from ej_conversations.models.favorites import FavoriteConversation
from .conversation_queryset import ConversationQuerySet
from .vote import Vote
from .vote_queryset import VoteQuerySet
from ..enums import Choice
from ej_integrations.models import RasaConversation


log = getLogger("ej")

#
# Exposed default managers
#
comments = Comment.approved
conversations = Conversation.objects.filter(is_hidden=False)
votes = Vote.objects


#
# Patch other models
#
def _patch():
    from django.contrib.auth import get_user_model
    from ej.utils.functional import deprecate_lazy
    from sidekick import lazy, property, placeholder as _

    #
    # Patch user model
    #
    user = get_user_model()

    # Enhanced querysets
    user.approved_comments = property(_.comments.approved())
    user.rejected_comments = property(_.comments.rejected())
    user.pending_comments = property(_.comments.pending())

    # Statistics
    user.n_conversations = lazy(_.conversations.count())
    user.n_total_comments = lazy(_.comments.count())
    user.n_approved_comments = lazy(_.approved_comments.count())
    user.n_pending_comments = lazy(_.pending_comments.count())
    user.n_rejected_comments = lazy(_.rejected_comments.count())
    user.n_votes = lazy(_.votes.count())
    user.n_final_votes = lazy(_.votes.exclude(choice=Choice.SKIP).count())

    # Deprecation warnings
    user.n_comments = deprecate_lazy(
        _.approved_comments.count(),
        'The "n_comments" attribute was deprecated in favor of "n_approved_comments"\n.'
        "This property will be removed in future versions of EJ.",
    )


_patch()
