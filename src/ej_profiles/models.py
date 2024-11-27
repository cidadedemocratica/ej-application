import hashlib
import logging

from constance import config
from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.storage import staticfiles_storage
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils.translation import gettext as __, gettext_lazy as _
from rest_framework.authtoken.models import Token
from sidekick import delegate_to, import_later
import toolz

from ej_conversations.models import Comment, Conversation, ConversationTag
from ej_conversations.models.vote import Vote

from .enums import Ethnicity, Gender, Race, Region, AgeRange, STATE_CHOICES_MAP
from .utils import years_from

SocialAccount = import_later("allauth.socialaccount.models:SocialAccount")
log = logging.getLogger("ej")
User = get_user_model()


class Profile(models.Model):
    """
    User profile
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    race = models.IntegerField(
        choices=Race.choices, default=Race.NOT_FILLED, verbose_name=_("Race")
    )
    ethnicity = models.CharField(_("Ethnicity"), blank=True, max_length=50)
    ethnicity_choices = models.IntegerField(
        choices=Ethnicity.choices, default=Ethnicity.NOT_FILLED
    )
    education = models.CharField(_("Education"), blank=True, max_length=140)
    gender = models.IntegerField(
        choices=Gender.choices,
        default=Gender.NOT_FILLED,
        verbose_name=("Gender identity"),
    )
    gender_other = models.CharField(_("User provided gender"), max_length=50, blank=True)
    birth_date = models.DateField(_("Birth Date"), null=True, blank=True)
    age_range = models.IntegerField(choices=AgeRange.choices, default=AgeRange.NOT_FILLED)
    country = models.CharField(_("Country"), blank=True, max_length=50)
    region = models.IntegerField(choices=Region.choices, default=Region.NOT_FILLED)
    state = models.CharField(_("State"), blank=True, max_length=3)
    city = models.CharField(_("City"), blank=True, max_length=140)
    biography = models.TextField(_("Biography"), blank=True)
    occupation = models.CharField(_("Occupation"), blank=True, max_length=50)
    political_activity = models.TextField(_("Political activity"), blank=True)
    profile_photo = models.ImageField(
        _("Profile Photo"), blank=True, null=True, upload_to="profile_images"
    )
    phone_number = models.CharField(_("Phone number"), blank=True, max_length=16)
    completed_tour = models.BooleanField(default=False, blank=True, null=True)
    filtered_home_tag = models.BooleanField(default=False, blank=True, null=True)

    # https://sidekick.readthedocs.io/en/latest/lib-properties.html?highlight=delegate_to#properties-and-descriptors
    name = delegate_to("user")
    email = delegate_to("user")
    is_active = delegate_to("user")
    is_staff = delegate_to("user")
    is_superuser = delegate_to("user")
    limit_board_conversations = delegate_to("user")

    @property
    def age(self):
        return None if self.birth_date is None else years_from(self.birth_date)

    class Meta:
        ordering = ["user__email"]

    def __str__(self):
        return __("{name}'s profile").format(name=self.user.name)

    def __getattr__(self, attr):
        try:
            user = self.user
        except User.DoesNotExist:
            raise AttributeError(attr)
        return getattr(user, attr)

    @property
    def gender_description(self):
        if self.gender != Gender.NOT_FILLED:
            return self.gender.label
        return self.gender_other

    @property
    def token(self):
        token = Token.objects.get_or_create(user_id=self.id)
        return token[0].key

    @property
    def image_url(self):
        try:
            return self.profile_photo.url
        except ValueError:
            if apps.is_installed("allauth.socialaccount"):
                for account in SocialAccount.objects.filter(user=self.user):
                    picture = account.get_avatar_url()
                    return picture
            return staticfiles_storage.url("/img/icons/navbar_profile.svg")

    @property
    def has_image(self):
        return bool(
            self.profile_photo
            or (
                apps.is_installed("allauth.socialaccount")
                and SocialAccount.objects.filter(user_id=self.id)
            )
        )

    @property
    def is_filled(self):
        fields = (
            "race",
            "age",
            "birth_date",
            "education",
            "ethnicity",
            "country",
            "state",
            "city",
            "biography",
            "occupation",
            "political_activity",
            "has_image",
            "gender_description",
            "phone_number",
        )
        return bool(all(getattr(self, field) for field in fields))

    def get_absolute_url(self):
        return reverse("user-detail", kwargs={"pk": self.id})

    def profile_fields(self, user_fields=False, blacklist=None):
        """
        Return a list of tuples of (field_description, field_value) for all
        registered profile fields.
        """

        fields = [
            "city",
            "state",
            "country",
            "occupation",
            "education",
            "ethnicity",
            "gender",
            "race",
            "political_activity",
            "biography",
            "phone_number",
        ]
        field_map = {field.name: field for field in self._meta.fields}
        null_values = {Gender.NOT_FILLED, Race.NOT_FILLED, None, ""}

        # Create a tuples of (attribute, human-readable name, value)
        triple_list = []
        for field in fields:
            description = field_map[field].verbose_name
            value = getattr(self, field)
            if value in null_values:
                value = None
            elif hasattr(self, f"get_{field}_display"):
                value = getattr(self, f"get_{field}_display")()
            triple_list.append((field, description, value))

        # Age is not a real field, but a property. We insert it after occupation
        triple_list.insert(3, ("age", _("Age"), self.age))

        # Add fields in the user profile (e.g., e-mail)
        if user_fields:
            triple_list.insert(0, ("email", _("E-mail"), self.user.email))

        # Prepare blacklist of fields and overrides
        if blacklist is None:
            blacklist = settings.EJ_PROFILE_EXCLUDE_FIELDS
        name_overrides = getattr(settings, "EJ_PROFILE_FIELD_NAMES", {})

        return list(prepare_fields(triple_list, blacklist, name_overrides))

    def statistics(self):
        """
        Return a dictionary with the participatory user's statistics.
        """
        return dict(
            votes=self.user.votes.count(),
            comments=self.user.comments.count(),
            conversations=self.user.conversations.count(),
        )

    def conversation_statistics(self, conversation: Conversation):
        """
        Return a dictionary containing the participatory user's statistics in the conversation.
        """
        approved_comments = conversation.comments.filter(
            status=Comment.STATUS.approved
        ).count()

        user_votes = Vote.objects.filter(
            comment__conversation_id=conversation.id, author=self.user
        )
        given_votes = 0
        if self.user.id:
            if config.RETURN_USER_SKIPED_COMMENTS:
                given_votes = user_votes.exclude(choice=0).count()
            else:
                given_votes = user_votes.count()

        e = 1e-50  # for numerical stability
        return {
            "votes": given_votes,
            "missing_votes": approved_comments - given_votes,
            "participation_ratio": given_votes / (approved_comments + e),
            "total_comments": approved_comments,
            "comments": given_votes,
        }

    def comments(self):
        """
        Return all profile comments.
        """
        return self.user.comments.all()

    def role(self):
        """
        A human-friendly description of the user role in the platform.
        """
        if self.user.is_superuser:
            return _("Root")
        if self.user.is_staff:
            return _("Administrative user")
        return _("Regular user")

    def get_state_display(self):
        return STATE_CHOICES_MAP.get(self.state, self.state) or _("(Not Filled)")

    def default_url(self):
        return reverse(("profile:home"))

    def participated_public_conversations(self):
        """
        Return conversations that an user has commented or voted
        """
        user = self.user
        return Conversation.objects.filter(
            Q(comments__author=user) | Q(comments__votes__author=user), is_promoted=True
        ).distinct()

    def participated_public_tags(self):
        """
        Return tags of conversations that an user has commented or voted
        """
        return ConversationTag.objects.filter(
            content_object__in=self.participated_public_conversations()
        ).distinct("tag")

    def get_contributions_data(self):
        # Fetch all conversations the user created
        created = self.user.conversations.cache_annotations(
            "first_tag", "n_user_votes", "n_comments", user=self.user
        ).order_by("-created")

        # Fetch voted conversations
        # This code merges in python 2 querysets. The first is annotated with
        # tag and the number of user votes. The second is annotated with the total
        # number of comments in each conversation
        voted = self.user.conversations_with_votes.exclude(id__in=[x.id for x in created])
        voted = voted.cache_annotations("first_tag", "n_user_votes", user=self.user)
        voted_extra = (
            Conversation.objects.filter(id__in=[x.id for x in voted])
            .cache_annotations("n_comments")
            .values("id", "n_comments")
        )
        total_votes = {}
        for item in voted_extra:
            total_votes[item["id"]] = item["n_comments"]
        for conversation in voted:
            conversation.annotation_total_votes = total_votes[conversation.id]

        # Now we get the favorite conversations from user
        favorites = Conversation.objects.filter(
            favorites__user=self.user
        ).cache_annotations("first_tag", "n_user_votes", "n_comments", user=self.user)

        comments = self.user.comments
        groups = toolz.groupby(lambda x: x.status, comments)
        approved = groups.get(Comment.STATUS.approved, ())
        rejected = groups.get(Comment.STATUS.rejected, ())
        pending = groups.get(Comment.STATUS.pending, ())

        return {
            "profile": self,
            "user": self.user,
            "created_conversations": created,
            "favorite_conversations": favorites,
            "voted_conversations": voted,
            "approved_comments": approved,
            "rejected_comments": rejected,
            "pending_comments": pending,
            "comments": comments,
        }


def prepare_fields(triples, blacklist, overrides):
    for a, b, c in triples:
        if a in blacklist:
            continue
        b = overrides.get(a, b)
        yield b, c


def gravatar_fallback(id_):
    """
    Computes gravatar fallback image URL from a unique string identifier
    """
    digest = hashlib.md5(id_.encode("utf-8")).hexdigest()
    return "https://gravatar.com/avatar/{}?s=40&d=mm".format(digest)


def get_profile(user, phone_number=""):
    """
    Return profile instance for user. Create profile if it does not exist.
    """
    try:
        return user.profile
    except Profile.DoesNotExist:
        profile = Profile.objects.create(user=user, phone_number=phone_number)
        log.info(f"{profile.user.email} profile successfully created")
        return profile


User.get_profile = get_profile
