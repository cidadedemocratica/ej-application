import logging
import random

from boogie.models import F, Value, IntegerField
from django.core.exceptions import FieldDoesNotExist
from boogie.models.wordcloud import WordCloudQuerySet
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from ej_conversations.enums import Choice

from .comment import Comment
from ..mixins import ConversationMixin

log = logging.getLogger("ej")


class ConversationQuerySet(ConversationMixin, WordCloudQuerySet):
    """
    A table of conversations.
    """

    conversations = lambda self: self

    def authors(self):
        """
        Return all authors from the current conversations.
        """
        return get_user_model().objects.filter(Q(conversations__in=self))

    def promoted(self):
        """
        Show only promoted conversations.
        """
        return self.filter(is_promoted=True, is_hidden=False)

    def cache_annotations(self, *values, user=None, prefix="", **kwargs):
        """
        Annotate each conversation with the progress made by the given user.
        """
        for arg in values:
            kwargs.setdefault(arg, True)

        annotations = self._get_annotations(kwargs, prefix or "", user)
        if kwargs:
            raise TypeError(f"bad attribute: {kwargs.popitem()[0]}")

        if not annotations:
            return self
        return self.annotate(**annotations)

    def _get_annotations(self, kwargs, prefix, user):
        annotations = {}

        # First tag
        if kwargs.pop("first_tag", False):
            ...
            # Fixme: does not work with Postgres. Disabling this creates a N+1
            # error fetching tags, but at least display conversations.
            # annotations[prefix + "first_tag"] = Window(FirstValue("tags__name"))

        # Count comments
        if kwargs.pop("n_comments", False):
            annotations[prefix + "n_comments"] = Count(
                "comments",
                filter=Q(comments__status=Comment.STATUS.approved),
                distinct=True,
            )

        # Count favorites
        if kwargs.pop("n_favorites", False):
            annotations[prefix + "n_favorites"] = Count("favorites")

        # Count votes
        if kwargs.pop("n_votes", False):
            annotations[prefix + "n_votes"] = Count("comments__votes")

        # Count votes for user
        if kwargs.pop("n_user_votes", False):
            if user.is_authenticated:
                data = Count("comments__votes", filter=Q(comments__votes__author=user))
            else:
                data = Value(0, IntegerField())
            annotations[prefix + "n_user_votes"] = data

        # Author name
        if kwargs.pop("author_name", False):
            annotations[prefix + "author_name"] = F(AUTHOR_NAME_FIELD)
        return annotations

    def random_votes(self, users=None, probs=(0.1, 0.15, 0.25)):
        """
        Cast random votes for the list of users.

        Args:
            users (sequence of users):
                List or queryset of users. Select all users if not given.
            probs:
                List of probabilities for (disagree, skip, agree). If normalized
                for less than 1, some users will not even cast any vote.
        """
        from .vote import Vote

        if not users:
            users = get_user_model().objects.filter(is_active=True)

        vote_prob = sum(probs)
        if vote_prob == 0:
            return  # Nothing to vote
        elif not 0 <= vote_prob <= 1:
            raise ValueError("sum o probabilities must be in [0, 1] interval")

        # Prepare to sample votes
        probs = [p / vote_prob for p in probs]
        choices = list(map(Choice.normalize, ["disagree", "skip", "agree"]))
        comments = self.comments()
        votes = set(map(tuple, comments.votes().values_list("comment_id", "author_id")))

        # Cast random votes
        new_votes = []
        for comment in comments:
            for user in users:
                if (comment.id, user.id) not in votes and random.random() < vote_prob:
                    choice = random.choices(choices, probs)[0]
                    vote = Vote(author=user, choice=choice, comment=comment)
                    new_votes.append(vote)

        return Vote.objects.bulk_create(new_votes)

    def filter_by_text_and_tag(self, search_text):
        if search_text:
            return self.filter(
                Q(text__icontains=search_text) | Q(tags__name__icontains=search_text)
            ).distinct()
        return self

    def filter_by_tags(self, tags):
        if tags:
            return self.filter(tags__name__in=tags).distinct()
        return self


#
# Constants and configurations
#
try:
    get_user_model()._meta.get_field("name")
    AUTHOR_NAME_FIELD = "author__name"
except FieldDoesNotExist:
    AUTHOR_NAME_FIELD = "author__username"
