from logging import getLogger

from boogie import models
from django.conf import settings
from django.db.models import OuterRef, Subquery
from django.utils.translation import gettext_lazy as _

from ej_conversations.enums import Choice
from .querysets import StereotypeQuerySet
from .stereotype_vote import StereotypeVote

log = getLogger("ej")


class Stereotype(models.Model):
    """
    A "fake" user created to help with classification.
    """

    name = models.CharField(
        _("Name"), max_length=64, help_text=_("Public identification of persona.")
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="stereotypes", on_delete=models.CASCADE
    )
    description = models.TextField(
        _("Description"),
        blank=True,
        help_text=_(
            "Specify a background history, or give hints about the profile this persona wants to "
            "capture. This information is optional and is not made public."
        ),
    )
    objects = StereotypeQuerySet.as_manager()

    class Meta:
        unique_together = [("name", "owner")]

    def __get_str__(self):
        return f"{self.name}"

    def vote(self, comment, choice, commit=True):
        """
        Cast a single vote for the stereotype.
        """
        choice = Choice.normalize(choice)
        log.debug(f"Vote: {self.name} (stereotype) - {choice}")
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
            votes.append(self.vote(comment, choice, commit=False))
        StereotypeVote.objects.bulk_update(votes)
        return votes

    def non_voted_comments(self, conversation):
        """
        Return a queryset with all comments that did not receive votes.
        """
        voted = StereotypeVote.objects.filter(
            author=self, comment__conversation=conversation
        )
        comment_ids = voted.values_list("comment", flat=True)
        return conversation.comments.exclude(id__in=comment_ids)

    def voted_comments(self, conversation):
        """
        Return a queryset with all comments that the stereotype has cast votes.

        The resulting queryset is annotated with the vote value using the choice
        attribute.
        """
        voted = StereotypeVote.objects.filter(
            author=self, comment__conversation=conversation
        )
        voted_subquery = voted.filter(comment=OuterRef("id")).values("choice")
        comment_ids = voted.values_list("comment", flat=True)
        return conversation.comments.filter(id__in=comment_ids).annotate(
            choice=Subquery(voted_subquery)
        )
