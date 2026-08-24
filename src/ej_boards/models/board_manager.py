from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from model_utils.models import TimeStampedModel


class BoardManager(TimeStampedModel):
    board = models.ForeignKey(
        "Board",
        on_delete=models.CASCADE,
        related_name="managers",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="managed_boards",
    )
    invitation = models.ForeignKey(
        "BoardManagerInvitation",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="managers",
    )

    class Meta:
        ordering = ["-created"]
        verbose_name = _("Board manager")
        verbose_name_plural = _("Board managers")
        constraints = [
            models.UniqueConstraint(
                fields=["board", "user"], name="unique_board_manager"
            )
        ]
        indexes = [
            models.Index(fields=["board", "user"], name="board_manager_idx"),
        ]

    def __str__(self):
        return f"{self.user} @ {self.board}"
