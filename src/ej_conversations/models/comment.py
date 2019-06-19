import logging

from boogie.rest import rest_api
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator
from django.db import models
from django.utils.translation import ugettext_lazy as _
from model_utils.choices import Choices
from model_utils.models import TimeStampedModel, StatusModel
from sidekick import lazy

from .utils import votes_counter
from .vote import Vote, normalize_choice, Choice
from ..managers import CommentManager
from ..validators import is_not_empty

log = logging.getLogger('ej-conversations')


@rest_api(['content', 'author', 'status', 'created', 'rejection_reason'])
class Comment(StatusModel, TimeStampedModel):
    """
    A comment on a conversation.
    """
    STATUS = Choices(
        ('pending', _('awaiting moderation')),
        ('approved', _('approved')),
        ('rejected', _('rejected')),
    )
    STATUS_MAP = {
        'pending': STATUS.pending,
        'approved': STATUS.approved,
        'rejected': STATUS.rejected,
    }
    REJECTION_REASON = Choices(
        ('incomplete_text', _('Incomplete or incomprehensible text')),
        ('off_topic', _('Off-topic')),
        ('offensive_language', _('Offensive content or language')),
        ('duplicated_comment', _('Duplicated content')),
        ('against_terms_of_service', _('Violates terms of service of the platform')),
    )
    conversation = models.ForeignKey(
        'Conversation',
        related_name='comments',
        on_delete=models.CASCADE,
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='comments',
        on_delete=models.CASCADE,
    )
    content = models.TextField(
        _('Content'),
        max_length=252,
        validators=[MinLengthValidator(2), is_not_empty],
        help_text=_('Body of text for the comment'),
    )
    rejection_reason = models.TextField(
        _('Rejection reason'),
        blank=True,
        help_text=_(
            'You must provide a reason to reject a comment. Users will receive '
            'this feedback.'
        ),
    )
    is_promoted = models.BooleanField(
        _('Promoted comment?'),
        default=False,
        help_text=_(
            'Promoted comments are prioritized when selecting random comments'
            'to users.'
        ),
    )
    is_approved = property(lambda self: self.status == self.STATUS.approved)
    is_pending = property(lambda self: self.status == self.STATUS.pending)
    is_rejected = property(lambda self: self.status == self.STATUS.rejected)

    @lazy
    def missing_votes(self):
        return Vote.objects.distinct().count() - self.total_votes

    # Statistics
    @property
    def agree_count(self):
        return votes_counter(self, choice=Choice.AGREE)

    @property
    def skip_count(self):
        return votes_counter(self, choice=Choice.SKIP)

    @property
    def disagree_count(self):
        return votes_counter(self, choice=Choice.DISAGREE)

    @property
    def total_votes(self):
        return self.agree_count + self.disagree_count + self.skip_count

    objects = CommentManager()

    class Meta:
        unique_together = ('conversation', 'content')

    def __str__(self):
        return self.content

    def clean(self):
        super().clean()
        if self.status == self.STATUS.rejected and not self.rejection_reason:
            msg = _('Must give a reason to reject a comment')
            raise ValidationError({'rejection_reason': msg})

    def vote(self, author, choice, commit=True):
        """
        Cast a vote for the current comment. Vote must be one of 'agree', 'skip'
        or 'disagree'.

        >>> comment.vote(request.user, 'agree')                 # doctest: +SKIP
        """
        choice = normalize_choice(choice)
        log.debug(f'Vote: {author} - {choice}')
        print('comment')
        print(self)
        print(choice)
        print(author.name)
        vote = Vote(author=author, comment=self, choice=choice)
        vote.full_clean()
        if commit:
            vote.save()
        return vote

    def statistics(self, ratios=False):
        """
        Return full voting statistics for comment.

        Args:
            ratios (bool):
                If True, also include 'agree_ratio', 'disagree_ratio', etc
                fields each original value. Ratios count the percentage of
                votes in each category.

        >>> comment.statistics()                            # doctest: +SKIP
        {
            'agree': 42,
            'disagree': 10,
            'skip': 25,
            'total': 67,
            'missing': 102,
        }
        """

        stats = {
            'agree': self.agree_count,
            'disagree': self.disagree_count,
            'skip': self.skip_count,
            'total': self.total_votes,
            'missing': self.missing_votes
        }

        if ratios:
            e = 1e-50  # prevents ZeroDivisionErrors
            stats.update(
                agree_ratio=self.agree_count / (self.total_votes + e),
                disagree_ratio=self.disagree_count / (self.total_votes + e),
                skip_ratio=self.skip_count / (self.total_votes + e),
                missing_ratio=self.missing_votes / (self.missing_votes + self.total_votes + e),
            )
        return stats

    @classmethod
    def campaign_comment(cls, rand_comment, campaign_comment_id, user):
        """
        Return campaign_comment_id comment if user not voted on it already.
        Otherwhise return rand_comment, that is the comment previusly selected
        by the view. This method will be used when the
        request come from a mail campaign.

        Args:
            rand_comment (Comment):
                comment previusly selected by the view.
            campaign_comment_id (string):
                comment id that was used on the mail campaign.
            user (User):
                logged user.
        """
        try:
            Vote.objects.get(author=user,comment=campaign_comment_id)
            return rand_comment
        except:
            return Comment.objects.get(id=campaign_comment_id)
