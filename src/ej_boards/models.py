from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from .utils import statistics
from model_utils.models import TimeStampedModel
from ej_users.models import User

from ej.utils.url import SafeUrl

from .validators import validate_board_slug


class Board(TimeStampedModel):
    """
    A board that contains a list of conversations.
    """

    PALETTE_CHOICES = (
        ("brand", _("Default")),
        ("accent", _("Alternative")),
        ("grey", _("Grey")),
        ("green", _("Green")),
        ("orange", _("Orange")),
        ("purple", _("Purple")),
    )
    slug = models.SlugField(
        _("Slug"), unique=True, validators=[validate_board_slug]
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="boards",
    )
    title = models.CharField(_("Title"), max_length=50)
    description = models.TextField(_("Description"), blank=True)
    palette = models.CharField(
        _("Palette"), max_length=10, choices=PALETTE_CHOICES, default="Blue"
    )
    image = models.ImageField(_("Image"), blank=True, null=True)
    users_favorite = models.ManyToManyField(
        User, default=[], related_name="favorite_boards"
    )

    statistics = statistics

    @property
    def tags(self):
        return [
            tag
            for conversation in self.conversations.all()
            for tag in conversation.tags.all()
        ]

    @property
    def conversations(self):
        return self.conversation_set.all()

    class Meta:
        verbose_name = _("Board")
        verbose_name_plural = _("Boards")

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.pk is None:
            self.slug = slugify(self.slug)
        super().save(*args, **kwargs)

    def clean(self):
        try:
            board = Board.objects.get(slug=self.slug)
            if board.slug == self.slug and board.id != self.id:
                raise ValidationError(_("Slug already exists."))
        except Board.DoesNotExist:
            pass

    def get_absolute_url(self):
        return reverse(
            "boards:conversation-list", kwargs={"board_slug": self.slug}
        )

    def url(self, which, **kwargs):
        kwargs["board"] = self
        return SafeUrl(which, **kwargs)

    def add_conversation(self, conversation):
        """
        Add conversation to board.
        """
        if conversation.id is None:
            conversation.save()
        self.conversation_set.add(conversation)

    def has_conversation(self, conversation):
        """
        Return True if conversation is present in board.
        """
        return conversation in self.conversations
