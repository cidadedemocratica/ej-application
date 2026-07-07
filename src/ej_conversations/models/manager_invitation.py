from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from model_utils.models import TimeStampedModel


class ConversationManagerInvitationQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)


class ConversationManagerInvitation(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        ACCEPTED = "accepted", _("Accepted")

    conversation = models.ForeignKey(
        "Conversation",
        on_delete=models.CASCADE,
        related_name="manager_invitations",
    )
    email = models.EmailField()
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conversation_manager_invitations",
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_conversation_manager_invitations",
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
    )
    is_active = models.BooleanField(default=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    send_error = models.TextField(blank=True)

    objects = ConversationManagerInvitationQuerySet.as_manager()

    class Meta:
        ordering = ["-created"]
        verbose_name = _("Conversation manager invitation")
        verbose_name_plural = _("Conversation manager invitations")
        constraints = [
            models.UniqueConstraint(
                fields=["conversation", "email"],
                condition=Q(is_active=True),
                name="unique_active_manager_invitation",
            )
        ]
        indexes = [
            models.Index(
                fields=["conversation", "email"],
                name="manager_inv_conv_email_idx",
            ),
            models.Index(fields=["user"], name="manager_inv_user_idx"),
        ]

    @staticmethod
    def normalize_email(email):
        return (email or "").strip().lower()

    def save(self, *args, **kwargs):
        self.email = self.normalize_email(self.email)
        super().save(*args, **kwargs)
        self.sync_manager()

    def resolve_user(self):
        """
        Return the invited user, using the linked user first and email fallback.
        """
        if self.user_id:
            return self.user

        email = self.normalize_email(self.email)
        if not email:
            return None

        return (
            get_user_model()
            .objects.annotate(normalized_email=Lower("email"))
            .filter(normalized_email=email)
            .first()
        )

    def sync_manager(self):
        """
        Create or update manager membership when this invitation is accepted.
        """
        from ej_conversations.models import ConversationManager

        user = self.resolve_user()
        is_accepted = (
            self.status == self.Status.ACCEPTED
            and self.is_active
            and user is not None
        )

        if not is_accepted:
            return None

        manager, created = ConversationManager.objects.get_or_create(
            conversation=self.conversation,
            user=user,
            defaults={"invitation": self},
        )
        if not created and manager.invitation_id != self.id:
            previous_invitation = manager.invitation
            manager.invitation = self
            manager.save(update_fields=["invitation"])
            if previous_invitation and previous_invitation.is_active:
                previous_invitation.is_active = False
                previous_invitation.save(update_fields=["is_active"])

        return manager

    def delete_manager(self):
        """Delete manager membership and invalidate this invitation."""
        from ej_conversations.models import ConversationManager

        ConversationManager.objects.filter(invitation=self).delete()
        if self.is_active:
            self.is_active = False
            self.save(update_fields=["is_active"])

    def accept(self, user=None):
        """Accept this invitation and ensure manager membership exists."""
        if not self.is_active:
            raise ValidationError(_("Inactive invitations cannot be accepted."))

        update_fields = []
        if user is not None and self.user_id != user.id:
            self.user = user
            update_fields.append("user")
        if self.status != self.Status.ACCEPTED:
            self.status = self.Status.ACCEPTED
            update_fields.append("status")

        if update_fields:
            self.save(update_fields=update_fields)
        return self

    def get_dashboard_url(self, request=None):
        url = reverse(
            "boards:dataviz-dashboard",
            kwargs=self.conversation.get_url_kwargs(),
        )
        if request is not None:
            return request.build_absolute_uri(url)
        return url

    def __str__(self):
        return self.email
