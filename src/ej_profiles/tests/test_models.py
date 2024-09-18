import datetime
from datetime import date
import pytest

from django.urls import reverse
from django.conf import settings
from django.utils.translation import gettext as _

from ej_conversations import create_conversation
from ej_conversations.enums import Choice
from ej_conversations.models.comment import Comment
from ej_conversations.models.vote import Vote
from ej_profiles.enums import Gender, Race
from ej_profiles.models import Profile
from ej_users.models import User
from ej_conversations.mommy_recipes import ConversationRecipes


@pytest.fixture
def other_user(db):
    user = User.objects.create_user("email2@server.com", "password")
    user.save()
    return user


class TestProfile(ConversationRecipes):
    @pytest.fixture
    def profile(self):
        return Profile(
            user=User(email="user@domain.com", name="name"),
            profile_photo="profile_photo",
            birth_date=date(1996, 1, 17),
            country="country",
            city="city",
            state="state",
            biography="biography",
            occupation="occupation",
            gender=Gender.FEMALE,
            political_activity="political_activity",
            race=Race.INDIGENOUS,
            ethnicity="ethnicity",
            education="undergraduate",
            phone_number="phone_number",
        )

    @pytest.mark.skipif(
        settings.EJ_THEME not in ("default", None),
        reason="Do not work if theme modify profile fields",
    )
    def test_profile_invariants(self, db, profile):
        profile.user.save()
        expected = {
            (_("City"), _("city")),
            (_("State"), _("state")),
            (_("Country"), _("country")),
            (_("Age"), profile.age),
            (_("Occupation"), _("occupation")),
            (_("Education"), _("undergraduate")),
            (_("Ethnicity"), _("ethnicity")),
            (_("Gender identity"), _("Female")),
            (_("Race"), _("Indigenous")),
            (_("Political activity"), _("political_activity")),
            (_("Biography"), _("biography")),
            (_("Phone number"), _("phone_number")),
        }
        assert str(profile) == _("name's profile")
        assert set(profile.profile_fields()) - expected == set()
        assert profile.is_filled
        assert profile.statistics() == {"votes": 0, "comments": 0, "conversations": 0}
        assert profile.role() == _("Regular user")

        # Remove a field
        profile.occupation = ""
        assert not profile.is_filled

    def test_profile_variants(self, db, profile):
        delta = datetime.datetime.now().date() - date(1996, 1, 17)
        age = abs(int(delta.days // 365.25))
        assert profile.age == age
        assert profile.gender_description == Gender.FEMALE.label
        profile.gender = Gender.NOT_FILLED
        assert profile.gender_description == profile.gender_other
        assert profile.has_image

    def test_user_profile_default_values(self, db):
        user = User.objects.create_user("email@at.com", "pass")
        profile = user.get_profile()
        assert profile.gender == Gender.NOT_FILLED
        assert profile.race == Race.NOT_FILLED
        assert profile.age is None
        assert profile.gender_other == ""
        assert profile.country == ""
        assert profile.state == ""
        assert profile.city == ""
        assert profile.biography == ""
        assert profile.occupation == ""
        assert profile.political_activity == ""
        assert profile.phone_number == ""

    def test_default_url_home(self, profile):
        profile_url = profile.default_url()
        assert profile_url == reverse("profile:home")

    def test_participated_on_promoted_conversation_vote(self, db, user, other_user):
        user.save()
        other_user.save()
        conversation = create_conversation(
            "this is the text", "this is the title", user, is_promoted=True
        )
        comment = Comment.objects.create(
            author=user, content="just a comment", conversation=conversation
        )
        Vote.objects.create(author=other_user, comment=comment, choice=Choice.AGREE)

        profile = other_user.get_profile()
        retrieved_conversation = profile.participated_public_conversations().first()

        assert retrieved_conversation == conversation

    def test_participated_private_conversation_vote(self, db, user, other_user):
        user.save()
        other_user.save()
        conversation = create_conversation("this is the text", "this is the title", user)
        comment = Comment.objects.create(
            author=user, content="just a comment", conversation=conversation
        )
        Vote.objects.create(author=other_user, comment=comment, choice=Choice.AGREE)

        profile = other_user.get_profile()
        retrieved_conversation = profile.participated_public_conversations().first()

        assert retrieved_conversation is None

    def test_participated_promoted_conversation_comment(self, db, user, other_user):
        user.save()
        other_user.save()
        conversation = create_conversation(
            "this is the text", "this is the title", user, is_promoted=True
        )
        Comment.objects.create(
            author=other_user, content="just a comment", conversation=conversation
        )

        profile = other_user.get_profile()
        retrieved_conversation = profile.participated_public_conversations().first()

        assert retrieved_conversation == conversation

    def test_participated_private_conversation_comment(self, db, user, other_user):
        user.save()
        other_user.save()
        conversation = create_conversation("this is the text", "this is the title", user)
        Comment.objects.create(
            author=other_user, content="just a comment", conversation=conversation
        )

        profile = other_user.get_profile()
        retrieved_conversation = profile.participated_public_conversations().first()

        assert retrieved_conversation is None

    def test_participated_conversation_comment_vote(self, db, user, other_user):
        user.save()
        other_user.save()
        conversation = create_conversation(
            "this is the text", "this is the title", user, is_promoted=True
        )
        comment = Comment.objects.create(
            author=user, content="just a comment", conversation=conversation
        )
        Vote.objects.create(author=other_user, comment=comment, choice=Choice.AGREE)

        other_conversation = create_conversation(
            "this is another text", "this is another title", user, is_promoted=True
        )
        Comment.objects.create(
            author=other_user,
            content="just another comment",
            conversation=other_conversation,
        )
        profile = other_user.get_profile()
        retrieved_conversations = profile.participated_public_conversations()

        assert conversation in retrieved_conversations
        assert other_conversation in retrieved_conversations
