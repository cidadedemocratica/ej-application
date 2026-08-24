from django.conf import settings
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from ej.manager_invitation import AbstractManagerInvitation


class BoardManagerInvitation(AbstractManagerInvitation):
    email_subject_template = _("%(inviter)s shared access to an EJ board")
    email_template_name = "ej_boards/manager-invitation-message.jinja2"

    board = models.ForeignKey(
        "Board",
        on_delete=models.CASCADE,
        related_name="manager_invitations",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="board_manager_invitations",
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_board_manager_invitations",
    )

    class Meta:
        ordering = ["-created"]
        verbose_name = _("Board manager invitation")
        verbose_name_plural = _("Board manager invitations")
        constraints = [
            models.UniqueConstraint(
                fields=["board", "email"],
                condition=Q(is_active=True),
                name="unique_active_board_manager_invitation",
            )
        ]
        indexes = [
            models.Index(
                fields=["board", "email"], name="board_manager_inv_email_idx"
            ),
            models.Index(fields=["user"], name="board_manager_inv_user_idx"),
        ]

    def get_manager_model(self):
        from .board_manager import BoardManager

        return BoardManager

    def get_manager_lookup(self, user):
        return {"board": self.board, "user": user}

    def get_accept_url(self, origin):
        path = reverse(
            "boards:board-accept_manager_invitation",
            kwargs={
                "board_slug": self.board.slug,
                "accept_token": self.accept_token,
            },
        )
        return f"{origin.rstrip('/')}{path}"

    def get_email_context(self):
        return {"board_title": self.board.title}

    def get_board_url(self):
        return self.board.get_absolute_url()

    def __str__(self):
        return self.email
