from django.db import models
from hashlib import blake2b
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from model_utils.choices import Choices
from model_utils.models import TimeStampedModel, StatusModel

from .comment_queryset import CommentQuerySet, log
from .vote import Vote
from ..enums import Choice, RejectionReason
from ..signals import vote_cast
from ..utils import votes_counter
from ..validators import is_not_empty


class Comment(StatusModel, TimeStampedModel):
    """
    A comment on a conversation.
    """

    STATUS = Choices(
        ("pending", _("awaiting moderation")),
        ("approved", _("approved")),
        ("rejected", _("rejected")),
    )
    STATUS_MAP = {
        "pending": STATUS.pending,
        "approved": STATUS.approved,
        "rejected": STATUS.rejected,
    }

    conversation = models.ForeignKey(
        "Conversation", related_name="comments", on_delete=models.CASCADE
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="comments", on_delete=models.CASCADE
    )
    content = models.TextField(
        _("Content"),
        max_length=252,
        validators=[MinLengthValidator(2), is_not_empty],
        help_text=_("Body of text for the comment"),
    )
    rejection_reason = models.IntegerField(
        choices=RejectionReason.choices, default=RejectionReason.USER_PROVIDED
    )
    rejection_reason_text = models.TextField(
        _("Rejection reason (free-form)"),
        blank=True,
        help_text=_(
            "You must provide a reason to reject a comment. Users will receive "
            "this feedback."
        ),
    )
    moderator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="moderated_comments",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    is_approved = property(lambda self: self.status == self.STATUS.approved)
    is_pending = property(lambda self: self.status == self.STATUS.pending)
    is_rejected = property(lambda self: self.status == self.STATUS.rejected)

    @property
    def has_rejection_explanation(self):
        return self.rejection_reason != RejectionReason.USER_PROVIDED or (
            self.rejection_reason.USER_PROVIDED and self.rejection_reason_text
        )

    @property
    def author_name(self):
        return self.author.name

    @property
    def missing_votes(self):
        return self.conversation.users.count() - self.n_votes

    @property
    def skip_count(self):
        return votes_counter(self, choice=Choice.SKIP)

    @property
    def disagree_count(self):
        return votes_counter(self, choice=Choice.DISAGREE)

    @property
    def agree_count(self):
        return votes_counter(self, choice=Choice.AGREE)

    @property
    def n_votes(self):
        return votes_counter(self)

    @property
    def rejection_reason_display(self):
        if self.status == self.STATUS.approved:
            return _("Comment is approved")
        elif self.status == self.STATUS.pending:
            return _("Comment is pending moderation")
        elif self.rejection_reason_text:
            return self.rejection_reason_text
        elif self.rejection_reason is not None:
            return self.rejection_reason.description
        else:
            raise AssertionError

    objects = CommentQuerySet.as_manager()

    class Meta:
        unique_together = ("conversation", "content")

    def __str__(self):
        return self.content

    def clean(self):
        super().clean()
        if self.status == self.STATUS.rejected and not self.has_rejection_explanation:
            raise ValidationError(
                {"rejection_reason": _("Must give a reason to reject a comment")}
            )

    def vote(self, author, choice, channel="ej", commit=True):
        """
        Cast a vote for the current comment. Vote must be one of 'agree', 'skip'
        or 'disagree'.

        >>> comment.vote(user, 'agree')                         # doctest: +SKIP
        """

        choice = Choice.normalize(choice)

        if self.is_pending:
            raise (ValidationError(_("Cannot vote on pending comment")))

        # We do not full_clean since the uniqueness constraint will only be
        # enforced when strictly necessary.
        vote = Vote(author=author, comment=self, choice=choice, channel=channel)
        vote.clean_fields()

        # Check if vote exists and if its existence represents an error
        is_changed = False
        try:
            saved_vote = Vote.objects.get(author=author, comment=self)
        except Vote.DoesNotExist:
            pass
        else:
            if saved_vote.choice == choice:
                commit = False
            elif saved_vote.choice == Choice.SKIP:
                vote.id = saved_vote.id
                vote.created = now()
                is_changed = True
            else:
                raise ValidationError("Cannot change user vote")

        # Send possibly saved vote
        if commit:
            vote.save()
            log.debug(f"Registered vote: {author} - {choice}")
            vote_cast.send(
                Comment,
                vote=vote,
                comment=self,
                choice=choice,
                is_update=is_changed,
                is_final=choice != Choice.SKIP,
            )
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
            "agree": self.agree_count,
            "disagree": self.disagree_count,
            "skip": self.skip_count,
            "total": self.n_votes,
            "missing": self.missing_votes,
        }

        if ratios:
            e = 1e-50  # prevents ZeroDivisionErrors
            stats.update(
                agree_ratio=self.agree_count / (self.n_votes + e),
                disagree_ratio=self.disagree_count / (self.n_votes + e),
                skip_ratio=self.skip_count / (self.n_votes + e),
                missing_ratio=self.missing_votes
                / (self.missing_votes + self.n_votes + e),
            )
        return stats

    def comment_url_hash(self):
        """
        Compute the URL hash for the given comment.
        """
        return blake2b(self.content.encode("utf8"), digest_size=4).hexdigest()
