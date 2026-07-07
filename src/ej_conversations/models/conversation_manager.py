from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from model_utils.models import TimeStampedModel


class ConversationManagerQuerySet(models.QuerySet):
    def is_manager(self, conversation, user):
        if not getattr(user, "is_authenticated", False) or user.pk is None:
            return False
        return self.filter(conversation=conversation, user=user).exists()


class ConversationManager(TimeStampedModel):
    conversation = models.ForeignKey(
        "Conversation",
        on_delete=models.CASCADE,
        related_name="managers",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="managed_conversations",
    )
    invitation = models.ForeignKey(
        "ConversationManagerInvitation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managers",
    )

    objects = ConversationManagerQuerySet.as_manager()

    class Meta:
        ordering = ["-created"]
        verbose_name = _("Conversation manager")
        verbose_name_plural = _("Conversation managers")
        constraints = [
            models.UniqueConstraint(
                fields=["conversation", "user"],
                name="unique_conversation_manager",
            )
        ]
        indexes = [
            models.Index(
                fields=["conversation", "user"],
                name="conversation_manager_idx",
            ),
        ]

    def __str__(self):
        return f"{self.user} @ {self.conversation}"
