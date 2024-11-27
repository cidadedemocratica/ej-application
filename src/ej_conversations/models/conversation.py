from datetime import datetime
import re

from autoslug import AutoSlugField
from boogie import models, rules
from ckeditor.fields import RichTextField
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models.functions import Length
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from ej.components.menu import CustomizeMenuMixin
from ej.utils.functional import deprecate_lazy
from ej.utils.url import SafeUrl
from ej_boards.models import Board
from ..validators import validate_file_size
from model_utils.models import TimeStampedModel
from sidekick import lazy, placeholder as this, property as property
from taggit.managers import TaggableManager
from taggit.models import TaggedItemBase

from ..enums import Choice
from ..signals import comment_moderated
from ..utils import normalize_status
from .comment import Comment
from .conversation_queryset import ConversationQuerySet, log
from .favorites import HasFavoriteMixin
from .util import (
    make_clean,
    statistics,
    vote_count,
    vote_distribution_over_time,
)
from .vote import Vote

NOT_GIVEN = object()


class Conversation(HasFavoriteMixin, CustomizeMenuMixin, TimeStampedModel):
    """
    A topic of conversation.
    """

    title = models.CharField(
        _("Title"),
        max_length=255,
        help_text=_("Short description used to create URL slugs (e.g. School system)."),
    )
    text = models.TextField(
        _("Question"),
        help_text=_(
            "What do you want to know from participants? The question is the central part of the conversation, from there you can create more specific comments."
        ),
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversations",
        help_text=_(
            "Only the author and administrative staff can edit this conversation."
        ),
    )
    moderators = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="moderated_conversations",
        help_text=_("Moderators can accept and reject comments."),
    )
    slug = AutoSlugField(unique=False, populate_from="title")
    board = models.ForeignKey(Board, on_delete=models.CASCADE, null=False, blank=False)
    is_promoted = models.BooleanField(
        _("Promote conversation?"),
        default=False,
        help_text=_(
            "Promoted conversations appears in the main /conversations/ " "endpoint."
        ),
    )
    is_hidden = models.BooleanField(
        _("Hide conversation?"),
        default=False,
        help_text=_(
            "Hidden conversations does not appears in boards or in the main /conversations/ "
            "endpoint."
        ),
    )
    anonymous_votes_enabled = models.BooleanField(
        default=False,
        blank=True,
        help_text=_(
            "Check this option if you want your audience to vote without registering. "
            "All users will be created with a random and unique ID."
        ),
        verbose_name=_("Enable anonymous votes"),
    )
    anonymous_votes = models.IntegerField(
        default=0,
        blank=True,
        help_text=_(
            "Configures how many anonymous votes the participants can give before "
            "asking him to register"
        ),
        verbose_name=_("Number of anonymous votes"),
    )
    send_profile_question = models.BooleanField(
        default=False,
        blank=True,
        verbose_name=_("Send profile question?"),
        help_text=_("Send a question to participants to complete their profile."),
    )
    votes_to_send_profile_question = models.IntegerField(
        default=0,
        blank=True,
        verbose_name=_("Votes to send profile question"),
        help_text=_("Number of votes to send profile question."),
    )
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    background_image = models.ImageField(
        upload_to="conversations/background/",
        blank=True,
        null=True,
        verbose_name=_("Background image"),
        validators=[validate_file_size],
    )
    logo_image = models.ImageField(
        upload_to="conversations/logo/",
        blank=True,
        null=True,
        verbose_name=_("Background image"),
        validators=[validate_file_size],
    )
    welcome_message = RichTextField(
        blank=True,
        null=True,
        help_text=_("A message to be presented to participants before starting voting."),
    )
    ending_message = RichTextField(
        blank=True,
        null=True,
        help_text=_("Text to be presented to participants in the end of voting."),
    )
    participants_can_add_comments = models.BooleanField(
        _("Participants will be able to add comments to this conversation."),
        default=True,
        help_text=_("Participants will be able to add comments to this conversation."),
    )

    objects = ConversationQuerySet.as_manager()
    tags = TaggableManager(through="ConversationTag", blank=True)
    votes = property(lambda self: Vote.objects.filter(comment__conversation=self))

    def set_overdue(self):
        """
        checks if conversation is a available for participation.
        """

        def end_date_is_bigger_then_today():
            return self.end_date and datetime.today().date() > self.end_date

        self.is_hidden = True if end_date_is_bigger_then_today() else False
        self.save()

    @property
    def users(self):
        return (
            get_user_model().objects.filter(votes__comment__conversation=self).distinct()
        )

    # Comment managers
    def _filter_comments(*args):
        *_, which = args
        status = getattr(Comment.STATUS, which)
        return property(lambda self: self.comments.filter(status=status))

    approved_comments = _filter_comments("approved")
    rejected_comments = _filter_comments("rejected")
    pending_comments = _filter_comments("pending")
    poll_comments = property(
        this.approved_comments.annotate(text_len=Length("content")).filter(
            text_len__lt=101
        )
    )
    del _filter_comments

    class Meta:
        ordering = ["created"]
        verbose_name = _("Conversation")
        verbose_name_plural = _("Conversations")
        permissions = (
            ("can_publish_promoted", _("Can publish promoted conversations")),
            ("is_moderator", _("Can moderate comments in any conversation")),
        )

    #
    # Statistics and annotated values
    #
    author_name = lazy(this.author.name)
    first_tag = lazy(this.tags.values_list("name", flat=True).first())
    tag_names = lazy(this.tags.values_list("name", flat=True))

    # Statistics
    n_comments = deprecate_lazy(
        this.n_approved_comments,
        "Conversation.n_comments was deprecated in favor of .n_approved_comments.",
    )
    n_approved_comments = lazy(this.approved_comments.count())
    n_pending_comments = lazy(this.pending_comments.count())
    n_rejected_comments = lazy(this.rejected_comments.count())
    n_total_comments = lazy(this.comments.count().count())

    n_favorites = lazy(this.favorites.count())
    n_tags = lazy(this.tags.count())
    n_votes = lazy(this.votes.count())
    n_final_votes = lazy(this.votes.exclude(choice=Choice.SKIP).count())
    n_participants = lazy(this.users.count())

    # Statistics for the request user
    user_comments = property(this.comments.filter(author=this.for_user))
    user_votes = property(this.votes.filter(author=this.for_user))
    n_user_total_comments = lazy(this.user_comments.count())
    n_user_comments = lazy(
        this.user_comments.filter(status=Comment.STATUS.approved).count()
    )
    n_user_rejected_comments = lazy(
        this.user_comments.filter(status=Comment.STATUS.rejected).count()
    )
    n_user_pending_comments = lazy(
        this.user_comments.filter(status=Comment.STATUS.pending).count()
    )
    n_user_votes = lazy(this.user_votes.count())
    n_user_final_votes = lazy(this.user_votes.exclude(choice=Choice.SKIP).count())
    is_user_favorite = lazy(this.is_favorite(this.for_user))

    # Statistical methods
    vote_count = vote_count
    statistics = statistics
    time_interval_votes = vote_distribution_over_time

    @lazy
    def for_user(self):
        return self.request.user

    @lazy
    def request(self):
        msg = "Set the request object by calling the .set_request(request) method first"
        raise RuntimeError(msg)

    # TODO: move as patches from other apps
    @lazy
    def n_clusters(self):
        try:
            return self.clusterization.n_clusters
        except AttributeError:
            return 0

    @lazy
    def n_stereotypes(self):
        try:
            return self.clusterization.n_clusters
        except AttributeError:
            return 0

    n_endorsements = 0  # FIXME: endorsements

    def __str__(self):
        return self.title

    def set_request(self, request_or_user):
        """
        Saves optional user and request attributes in model. Those attributes are
        used to compute and cache many other attributes and statistics in the
        conversation model instance.
        """
        request = None
        user = request_or_user
        if not isinstance(request_or_user, get_user_model()):
            user = request_or_user.user
            request = request_or_user

        if (
            self.__dict__.get("for_user", user) != user
            or self.__dict__.get("request", request) != request
        ):
            raise ValueError("user/request already set in conversation!")

        self.for_user = user
        self.request = request

    def save(self, *args, **kwargs):
        if self.id is None:
            pass
        super().save(*args, **kwargs)

    def clean(self):
        can_edit = "ej.can_edit_conversation"
        if (
            self.is_promoted
            and self.author_id is not None
            and not self.author.has_perm(can_edit, self)
        ):
            raise ValidationError(
                _("User does not have permission to create a promoted " "conversation.")
            )

    def get_absolute_url(self, board=None):
        if board is None:
            board = getattr(self, "board", None)
        if board:
            kwargs = self.get_url_kwargs()
            return reverse("boards:conversation-detail", kwargs=kwargs)
        else:
            raise ValidationError("Board should not be None")

    def url(self, which="boards:conversation-detail", board=None, **kwargs):
        """
        Return a url pertaining to the current conversation.
        """

        if board is None:
            board = getattr(self, "board", None)

        kwargs["conversation"] = self
        kwargs["slug"] = self.slug

        if board:
            kwargs["board"] = board
            which = "boards:" + which.replace(":", "-")
            return SafeUrl(which, **kwargs)

        return SafeUrl(which, **kwargs)

    def patch_url(self, which, board=None, **kwargs):
        """
        Return a url pertaining to the current conversation.
        """
        if board is None:
            board = getattr(self, "board", None)

        kwargs["conversation_id"] = self.id
        kwargs["slug"] = self.slug

        if board:
            kwargs["board_slug"] = board.slug
            which = "boards:" + which.replace(":", "-")
            return SafeUrl(which, **kwargs)

        raise ValidationError("Board should not be None")

    def get_url_kwargs(self):
        return {
            "conversation_id": self.id,
            "slug": self.slug,
            "board_slug": self.board.slug,
        }

    def votes_for_user(self, user):
        """
        Get all votes in conversation for the given user.
        """
        if user.id is None:
            return Vote.objects.none()
        return self.votes.filter(author=user)

    def create_comment(
        self, author, content, commit=True, *, status=None, check_limits=True, **kwargs
    ):
        """
        Create a new comment object for the given user.

        If commit=True (default), comment is persisted on the database.

        By default, this method check if the user can post according to the
        limits imposed by the conversation. It also normalizes duplicate
        comments and reuse duplicates from the database.
        """

        # Convert status, if necessary
        if status is None and (
            author.id == self.author.id
            or author.has_perm("ej.can_edit_conversation", self)
        ):
            kwargs["status"] = Comment.STATUS.approved

        else:
            kwargs["status"] = normalize_status(status)

        # Check limits
        if check_limits and not author.has_perm("ej.can_comment", self):
            log.info("failed attempt to create comment by %s" % author)
            raise PermissionError("user cannot comment on conversation.")

        kwargs.update(author=author, content=content.strip())
        comment = make_clean(Comment, commit, conversation=self, **kwargs)
        if comment.status == comment.STATUS.approved and author != self.author:
            comment_moderated.send(
                Comment,
                comment=comment,
                moderator=comment.moderator,
                is_approved=True,
                author=comment.author,
            )
        log.info("new comment: %s" % comment)
        return comment

    def next_comment(self, user, random=True):
        """
        Returns a random comment that user didn't vote yet.

        If default value is not given, raises a Comment.DoesNotExit exception
        if no comments are available for user.

        :param random: when False, next_comment will return the same comment.
        :type random: bool
        """
        approved_comments = self.approved_comments
        if not user or user.is_anonymous:
            return approved_comments.first()
        if random:
            comment = rules.compute("ej.next_comment", self, user)
            return comment or None
        return approved_comments.exclude(votes__author=user).first()

    def next_comment_with_id(self, user, comment_id=None):
        """
        Returns a comment with id if user didn't vote yet, otherwhise return
        a random comment.
        """
        if not user or user.is_anonymous:
            return self.approved_comments.first()

        if comment_id:
            try:
                return self.approved_comments.exclude(votes__author=user).get(
                    id=comment_id
                )
            except Exception:
                pass
        return self.next_comment(user)

    def reaches_anonymous_particiption_limit(self, user):
        """
        Check if user is anonymous and has reached the anonymous votes limit.
        """
        user_is_anonymous = user.is_anonymous or re.match(
            r"^anonymoususer-.*", user.email
        )
        return (
            (user_is_anonymous or not user.has_completed_registration)
            and self.anonymous_votes
            and self.votes.filter(author=user).count() == self.anonymous_votes
        )

    def user_progress_percentage(self, user):
        total = self.n_approved_comments
        n = 0
        if not user.is_anonymous:
            self.for_user = user
            n = self.n_user_final_votes
            n = min(n, total)
        if total < 1:
            return 1
        return round((n / total) * 100)

    def current_comment_count(self, user):
        self.for_user = user
        n_user_final_votes = self.n_user_final_votes

        if self.n_approved_comments == n_user_final_votes:
            return n_user_final_votes
        return n_user_final_votes + 1

    def user_can_add_comment(self, user, user_comments: int):
        """
        check if user can add new comments to conversation

        :param user_comments: number of comments created by user
        :param max_comments: max comments allowed per user
        """
        return (
            user_comments < rules.compute("ej.max_comments_per_conversation")
            or user.is_superuser
            or self.author == user
        )

    def get_background_image_url(self, host):
        background_image_url = self.background_image

        if background_image_url:
            return f"{host}/media/{background_image_url}"
        return None

    def get_logo_image_url(self, host):
        logo_image_url = self.logo_image

        if logo_image_url:
            return f"{host}/media/{logo_image_url}"
        return None


#
#  AUXILIARY MODELS
#
class ConversationTag(TaggedItemBase):
    """
    Add tags to Conversations with real Foreign Keys
    """

    content_object = models.ForeignKey("Conversation", on_delete=models.CASCADE)
