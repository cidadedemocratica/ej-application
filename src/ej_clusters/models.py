import logging
from random import randrange

import pandas as pd
import sidekick as sk
from autoslug import AutoSlugField
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Subquery, OuterRef
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel
from sidekick import delegate_to, alias, lazy

from boogie import rules
from boogie.fields import EnumField
from boogie.rest import rest_api
from ej_conversations.managers import BoogieManager
from ej_conversations.models import Choice, Conversation
from ej_conversations.models.vote import normalize_choice
from .manager import ClusterManager
from .types import ClusterStatus

log = logging.getLogger('ej')
math = sk.import_later('.math', package=__package__)


@rest_api()
class Clusterization(TimeStampedModel):
    """
    Manages clusterization tasks for a given conversation.
    """
    conversation = models.OneToOneField(
        'ej_conversations.Conversation',
        on_delete=models.CASCADE,
        related_name='clusterization',
    )
    cluster_status = EnumField(
        ClusterStatus,
        default=ClusterStatus.PENDING_DATA,
    )
    unprocessed_votes = models.PositiveSmallIntegerField(
        default=0,
        editable=False,
    )
    unprocessed_comments = models.PositiveSmallIntegerField(
        default=0,
        editable=False,
    )

    @property
    def stereotypes(self):
        return Stereotype.objects.filter(clusters__in=self.clusters.all())

    class Meta:
        ordering = ['conversation_id']

    def __str__(self):
        clusters = self.clusters.count()
        return f'{self.conversation} ({clusters} clusters)'

    def get_absolute_url(self):
        args = {'conversation': self.conversation}
        return reverse('cluster:index', kwargs=args)

    def update(self, commit=True):
        """
        Update clusters if necessary.
        """
        if self.requires_update():
            self.force_update(commit=False)
            if self.cluster_status == ClusterStatus.PENDING_DATA:
                self.cluster_status = ClusterStatus.ACTIVE
        if commit:
            self.save()

    def force_update(self, commit=True):
        """
        Force a cluster update.

        Used internally by .update() when an update is necessary.
        """
        log.info(f'[clusters] updating cluster: {self.conversation}')

        math.update_clusters(self.conversation, self.clusters.all())
        self.unprocessed_comments = 0
        self.unprocessed_votes = 0
        if commit:
            self.save()

    def requires_update(self):
        """
        Check if update should be recomputed.
        """
        conversation = self.conversation
        if self.cluster_status == ClusterStatus.PENDING_DATA:
            rule = rules.get_rule('ej.conversation_can_start_clusterization')
            if not rule.test(conversation):
                log.info(f'[clusters] {conversation}: not enough data to start clusterization')
                return False
        elif self.cluster_status == ClusterStatus.DISABLED:
            return False

        rule = rules.get_rule('ej.conversation_must_update_clusters')
        return rule.test(conversation)


@rest_api(exclude=['users', 'stereotypes'])
class Cluster(TimeStampedModel):
    """
    Represents an opinion group.
    """

    clusterization = models.ForeignKey(
        'Clusterization',
        on_delete=models.CASCADE,
        related_name='clusters',
    )
    name = models.CharField(
        _('Name'),
        max_length=64,
    )
    description = models.TextField(
        _('Description'),
        blank=True,
        help_text=_(
            'How was this cluster conceived?'
        ),
    )
    slug = AutoSlugField(
        null=True,
        unique=True,
        populate_from='name',
    )
    users = models.ManyToManyField(
        get_user_model(),
        related_name='clusters',
        blank=True,
    )
    stereotypes = models.ManyToManyField(
        'Stereotype',
        related_name='clusters',
    )

    conversation = delegate_to('clusterization')
    objects = ClusterManager()

    def __str__(self):
        msg = _('{name} ("{conversation}" conversation)')
        return msg.format(name=self.name, conversation=str(self.conversation))

    def get_absolute_url(self):
        args = {
            'conversation': self.conversation,
            'cluster': self,
        }
        return reverse('cluster:detail', kwargs=args)

    def mean_stereotype(self):
        """
        Return the mean stereotype for cluster.
        """
        stereotypes = self.stereotypes.all()
        votes = (
            StereotypeVote.objects
                .filter(author__in=Subquery(stereotypes.values('id')))
                .values_list('comment', 'choice')
        )
        df = pd.DataFrame(list(votes), columns=['comment', 'choice'])
        if len(df) == 0:
            return pd.DataFrame([], columns=['choice'])
        else:
            return df.pivot_table('choice', index='comment', aggfunc='mean')


class Stereotype(models.Model):
    """
    A "fake" user created to help with classification.
    """

    name = models.CharField(
        _('Name'),
        max_length=64,
    )
    conversation = models.ForeignKey(
        'ej_conversations.Conversation',
        on_delete=models.CASCADE,
        related_name='stereotypes',
        help_text=_(
            'Conversation associated with the stereotype.'
        ),
        null=True, blank=True,
    )
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    description = models.TextField(
        _('Description'),
        blank=True,
        help_text=_(
            'A detailed description of your stereotype for future reference. '
            'You can specify a background history, or give hints on the exact '
            'profile the stereotype wants to capture.'
        ),
    )

    class Meta:
        unique_together = [('name', 'conversation')]

    __str__ = (lambda self: self.name)

    def vote(self, comment, choice, commit=True):
        """
        Cast a single vote for the stereotype.
        """
        choice = normalize_choice(choice)
        log.debug(f'Vote: {self.name} (stereotype) - {choice}')
        vote = StereotypeVote(author=self, comment=comment, choice=choice)
        vote.full_clean()
        if commit:
            vote.save()
        return vote

    def cast_votes(self, choices):
        """
        Create votes from dictionary of comments to choices.
        """
        votes = []
        for comment, choice in choices.items():
            votes.append(self.vote(comment, choice, commit=True))
        StereotypeVote.objects.bulk_update(votes)
        return votes

    def next_comment(self, conversation):
        """
        Get next available comment for the given conversation.
        """
        remaining = self.non_voted_comments(conversation)
        size = remaining.count()
        return remaining[randrange(size)]

    def non_voted_comments(self, conversation):
        """
        Return a queryset with all comments that did not receive votes.
        """
        voted = StereotypeVote.objects.filter(
            author=self,
            comment__conversation=conversation,
        )
        comment_ids = voted.values_list('comment', flat=True)
        return conversation.comments.exclude(id__in=comment_ids)

    def voted_comments(self, conversation):
        """
        Return a queryset with all comments that the stereotype has cast votes.

        The resulting queryset is annotated with the vote value using the choice
        attribute.
        """
        voted = StereotypeVote.objects.filter(
            author=self,
            comment__conversation=conversation,
        )
        voted_subquery = (
            voted
                .filter(comment=OuterRef('id'))
                .values('choice')
        )
        comment_ids = voted.values_list('comment', flat=True)
        return (
            conversation.comments
                .filter(id__in=comment_ids)
                .annotate(choice=Subquery(voted_subquery))
        )


class StereotypeVote(models.Model):
    """
    Similar to vote, but it is not associated with a comment.

    It forms a m2m relationship between Stereotypes and comments.
    """
    author = models.ForeignKey(
        'Stereotype',
        related_name='votes',
        on_delete=models.CASCADE,
    )
    comment = models.ForeignKey(
        'ej_conversations.Comment',
        verbose_name=_('Comment'),
        related_name='stereotype_votes',
        on_delete=models.CASCADE,
    )
    choice = EnumField(Choice, _('Choice'))
    stereotype = alias('author')
    objects = BoogieManager()

    def __str__(self):
        return f'StereotypeVote({self.author}, value={self.choice})'


#
# Auxiliary methods
#
def get_clusterization(conversation):
    try:
        return conversation.clusterization
    except Clusterization.DoesNotExist:
        mgm, _ = Clusterization.objects.get_or_create(conversation=conversation)
        return mgm


Conversation.get_clusterization = get_clusterization
Conversation._clusterization = lazy(get_clusterization)
Conversation.clusters = delegate_to('_clusterization')
