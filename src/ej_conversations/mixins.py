from collections.abc import Iterable
from random import randrange

from boogie import db
from boogie.models import QuerySet
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext
import pandas as pd
from sidekick import import_later

from .math import votes_statistics

np = import_later("numpy")
NOT_GIVEN = object()


class ConversationMixin:
    """
    Implements an interface with a predictable route to fetch conversations,
    comments and votes related to the current queryset.

    Different models may interpret this relation slightly different, and this
    mixin just implements sane defaults.
    """

    def _votes_from_comments(self, comments):
        return comments.votes()

    def random(self, default=NOT_GIVEN):
        """
        Returns a random element.
        """
        size = self.count()
        if size == 0 and default is NOT_GIVEN:
            raise self.model.DoesNotExist
        elif size == 0:
            return default
        else:
            return self[randrange(size)]

    def conversations(self):
        """
        Return queryset with all conversations associated with the current
        queryset.
        """
        raise NotImplementedError("must be overridden in subclass")

    def comments(self, conversation=None):
        """
        Return queryset with all comments associated with the current
        queryset.
        """
        conversations = self.conversations()
        qs = db.ej_conversations.comments.filter(conversation__in=conversations)
        if conversation:
            qs = qs.filter(**conversation_filter(conversation, qs))
        return qs

    def votes(self, conversation=None, comments=None):
        """
        Return a queryset of all votes from the given authors.

        Args:
            conversation:
                Filter comments by conversation, if given. Can be a conversation
                instance, an id, or a queryset.
            comments:
                An optional queryset of comments to filter the return set of
                votes. If given as queryset, ignore the conversation parameter.
        """
        if comments is None:
            comments = self.comments(conversation)
        elif not isinstance(comments, QuerySet):
            comments = self.comments(conversation).filter(comments__in=comments)
        return self._votes_from_comments(comments)

    def votes_table(self, data_imputation=None, conversation=None, comments=None):
        """
        An alias to self.votes().table(), accepts parameters of both functions.
        """
        return self.votes(conversation, comments).votes_table(data_imputation)


class UserMixin(ConversationMixin):
    extend_dataframe = QuerySet.extend_dataframe

    def comments(self, conversation=None):
        """
        Return a comments queryset with all comments voted by the given
        users.

        Args:
            conversation:
                Filter comments by conversation, if given. Can be a conversation
                instance, an id, or a queryset.
        """
        votes = db.ej_conversations.vote_objects.filter(author__in=self)
        comments = db.ej_conversations.comments.filter(votes__in=votes)
        if conversation:
            comments = comments.filter(**conversation_filter(conversation))
        return comments

    def statistics_summary_dataframe(
        self,
        normalization=1,
        votes=None,
        comments=None,
        extend_fields=(),
        convergence=True,
        participation=True,
        conversation=None,
    ):
        """
        Return a dataframe with basic voting statistics.

        The resulting dataframe has the 'author', 'text', 'agree', 'disagree'
        'skipped', 'convergence' and 'participation' columns.
        """

        if votes is None and comments is None:
            votes = db.ej_conversations.votes.filter(
                author__in=self, comment__conversation=conversation
            )
        if votes is None:
            votes = comments.votes().filter(
                author__in=self, comment__conversation=conversation
            )

        votes = votes.dataframe("comment", "author", "choice")
        votes_statistics_df = votes_statistics(
            votes, participation=participation, convergence=convergence, ratios=True
        )
        votes_statistics_df *= normalization

        # Extend fields with additional data
        extend_full_fields = [EXTEND_FIELDS.get(x, x) for x in extend_fields]

        # Save extended dataframe
        extend_fields = list(extend_fields)
        votes_statistics_df = self.extend_dataframe(
            votes_statistics_df, "name", "email", "date_joined", *extend_full_fields
        )
        if extend_fields:
            columns = list(votes_statistics_df.columns[: -len(extend_fields)])
            columns.extend(extend_fields)
            votes_statistics_df.columns = columns
        cols = [
            "name",
            "email",
            "date_joined",
            *extend_fields,
            "agree",
            "disagree",
            "skipped",
            *(["convergence"] if convergence else ()),
            *(["participation"] if participation else ()),
        ]
        votes_statistics_df = votes_statistics_df[cols]

        # Retrieve in a single queryset the conversation clusters and the clustered participants.
        # The queryset is converted to a list of tuples. Each tuple has the user email and his cluster.
        users_clusters = list(
            db.ej_clusters.clusters.filter(clusterization__conversation=conversation)
            .prefetch_related("users")
            .values_list("users__email", "name")
        )

        # Convert the list of tuples to a Pandas Dataframe.
        users_clusters_df = pd.DataFrame(users_clusters, columns=["email", "group"])

        # Merge the votes Dataframe with the clusters Dataframe.
        votes_statistics_df = votes_statistics_df.merge(users_clusters_df, how="outer")

        # Fix the Dataframe lines without a valid cluster.
        votes_statistics_df[["group"]] = votes_statistics_df[["group"]].fillna(
            gettext("No group")
        )

        return votes_statistics_df


#
# Auxiliary functions
#
def conversation_filter(conversation, field="conversation"):
    if isinstance(conversation, int):
        return {field + "_id": conversation}
    elif isinstance(conversation, db.conversation_model):
        return {field: conversation}
    elif isinstance(conversation, (QuerySet, Iterable)):
        return {field + "__in": conversation}
    else:
        raise ValueError(f"invalid value for conversation: {conversation}")


#
# Patch user class
#
def patch_user_class():
    qs_type = type(get_user_model().objects.get_queryset())
    manager_type = type(get_user_model().objects)

    if qs_type in (QuerySet, *QuerySet.__bases__):
        # We take special actions for Django's builtin user model
        from django.contrib.auth.models import User, UserManager

        if get_user_model() is User:
            UserManager._queryset_class = type(
                "UserQueryset", (UserMixin, UserManager._queryset_class), {}
            )
            return
        else:
            raise ImproperlyConfigured(
                "You cannot use a generic QuerySet for your user model.\n"
                "ej_conversations have to patch the queryset class for this model and\n"
                "by adding a new base class and we do not want to patch the base\n"
                "QuerySet since that would affect all models."
            )

    qs_type.__bases__ = (UserMixin, *qs_type.__bases__)
    manager_type.__bases__ = (UserMixin, *manager_type.__bases__)


patch_user_class()


def is_empty(x):
    try:
        return x is None or np.isnan(x)
    except TypeError:
        return not bool(x)


#
# Constants
#
EXTEND_FIELDS = {
    "gender": "profile__gender",
    "race": "profile__race",
    "education": "profile__education",
    "occupation": "profile__occupation",
    "birth_date": "profile__birth_date",
    "country": "profile__country",
    "state": "profile__state",
    "age": "profile__birth_date",
}
