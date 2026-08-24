from django.conf import settings
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from ej.manager_invitation import AbstractManagerInvitation


class ConversationManagerInvitation(AbstractManagerInvitation):
    email_subject_template = _(
        "%(inviter)s shared access to an EJ conversation"
    )
    email_template_name = "ej_conversations/manager-invitation-message.jinja2"

    conversation = models.ForeignKey(
        "Conversation",
        on_delete=models.CASCADE,
        related_name="manager_invitations",
    )
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

    def get_manager_model(self):
        from .conversation_manager import ConversationManager

        return ConversationManager

    def get_manager_lookup(self, user):
        return {"conversation": self.conversation, "user": user}

    def get_accept_url(self, origin):
        path = reverse(
            "boards:conversation-accept_manager_invitation",
            kwargs={
                **self.conversation.get_url_kwargs(),
                "accept_token": self.accept_token,
            },
        )
        return f"{origin.rstrip('/')}{path}"

    def get_email_context(self):
        return {"conversation_title": self.conversation.title}

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
