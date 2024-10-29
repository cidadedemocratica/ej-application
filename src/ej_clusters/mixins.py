from django.contrib.auth import get_user_model

from boogie import db
from ej_conversations.mixins import ConversationMixin

db = db.ej_clusters


class ClusterizationBaseMixin(ConversationMixin):
    """
    Mixin class with common implementations for Clusterization and Cluster
    querysets.
    """

    def stereotype_votes(self, comments=None):
        """
        Return queryset with all votes associated with the current
        queryset.
        """
        if comments is None:
            comments = self.comments()
        return db.stereotypevotes.filter(comment__in=comments)

    def clusters(self):
        """
        Return queryset with all clusters associated with the current queryset.
        """
        return db.clusters.filter(clusterization__in=self)

    def stereotypes(self):
        """
        Return queryset with all stereotypes associated with the current
        queryset.
        """
        if self.model.__name__ == "Cluster":
            return db.stereotypes.filter(clusters__in=self)
        return db.stereotypes.filter(clusters__in=self.clusters())

    def users(self, by_comment=False):
        """
        Return queryset with all stereotypes associated with the current
        queryset.

        Args:
            by_comment:
                If True, fetches only users who commented in the conversation.
        """
        users = get_user_model().objects

        if by_comment:
            return users.filter(comments__in=self.comments())
        else:
            return users.filter(votes__in=self.votes())
