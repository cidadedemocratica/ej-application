import pandas as pd
from django.contrib.auth import get_user_model

from ej_clusters.math import get_raw_votes
from ej_conversations import models
from ej_math import VoteStats

User = get_user_model()


def update(cls):
    """
    Update class with all methods and attributes in the given mixin.
    """

    def decorator(mixin):
        for attr in vars(mixin):
            if attr.startswith('__'):
                continue
            value = getattr(mixin, attr)
            setattr(cls, attr, value)

    return decorator


@update(models.Conversation)
class ConversationMixin:
    _votes_dataframe = None

    def votes_dataframe(self, cache=False):
        if cache:
            if self._votes_dataframe is None:
                self._votes_dataframe = self.votes_dataframe(cache=False)
            return self._votes_dataframe
        return get_raw_votes(self)

    def comments_dataframe(self, votes=None, cache=False):
        """
        Data frame with information about each comment in conversation.
        """
        if votes is None:
            votes = self.votes_dataframe(cache)

        stats = VoteStats(votes)
        df = stats.comments(pc=True)
        comments = self.comments.approved().display_dataframe()
        comments = comments[['id', 'author', 'text']]
        for col in ['agree', 'disagree', 'skipped', 'divergence']:
            comments[col] = df[col]

        comments['participation'] = 100 - df['missing']
        comments.dropna(inplace=True)
        remaining = 100 - comments['skipped']
        comments['agree'] = 0.01 * comments['agree'] * remaining
        comments['disagree'] = 0.01 * comments['disagree'] * remaining
        return comments

    def participants_dataframe(self, votes=None, cache=False):
        """
        Data frame with information about each participant in conversation.
        """
        if votes is None:
            votes = self.votes_dataframe(cache)
        stats = VoteStats(votes)
        df = stats.users(pc=True)

        data = list(User.objects.values_list('email', 'name'))
        participants = pd.DataFrame(data, columns=['email', 'name'])
        participants.index = participants.pop('email')

        for col in ['agree', 'disagree', 'skipped', 'divergence']:
            participants[col] = df[col]

        return participants
