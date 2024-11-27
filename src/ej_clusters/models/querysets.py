from sidekick import import_later

from boogie.models import QuerySet, Manager
from ej_conversations import Choice
from ej_conversations.mixins import UserMixin, conversation_filter
from ej_conversations.models import Conversation, VoteQuerySet, Comment, CommentQuerySet
from ..mixins import ClusterizationBaseMixin

models = import_later("..models", package=__package__)


class ClusterizationQuerySet(ClusterizationBaseMixin, QuerySet):
    """
    A table of Clusterizations.
    """

    def conversations(self):
        return Conversation.objects.filter(clusterization__in=self)


class ClusterizationManager(Manager.from_queryset(ClusterizationQuerySet)):
    def create_with_stereotypes(self):
        """
        Create clusterization with the given stereotypes.
        """
        raise NotImplementedError


class StereotypeVoteQuerySet(QuerySet):
    """
    A table of StereotypeVotes.
    """

    def get_votes(self):
        return self

    votes_table = VoteQuerySet.votes_table


class StereotypeQuerySet(UserMixin, QuerySet):
    """
    A table of Stereotypes.
    """

    def _votes_from_comments(_, comments):
        return comments.stereotype_votes()

    def fill_votes(self, choice=Choice.DISAGREE, comments=None):
        """
        Gather all comments voted by the current queryset and fill the votes of
        the other stereotypes with the given vote.

        Args:
            choice:
                The choice to fill in (agree, disagree, etc)
            comments:
                Optionally restrict votes to the comments in the given
                queryset, if given.

        Returns:
            None
        """
        raise NotImplementedError

    def comments(self, conversation=None):
        """
        Return a comments queryset with all comments voted by the given
        stereotypes.

        Args:
            conversation:
                Filter comments by conversation, if given. Can be a conversation
                instance, an id, or a queryset.
        """
        votes = models.StereotypeVote.objects.filter(author__in=self)
        comments = Comment.objects.filter(stereotype_votes__in=votes)
        if conversation:
            comments = comments.filter(**conversation_filter(conversation))
        return comments


#
# PATCH STANDARD COMMENT QUERYSET
#
class CommentQuerySetMixin:
    def stereotype_votes(self):
        """
        Return a queryset with all stereotype votes related to the current
        comments.
        """
        return models.StereotypeVote.objects.filter(comment__in=self)


CommentQuerySet.stereotype_votes = CommentQuerySetMixin.stereotype_votes
