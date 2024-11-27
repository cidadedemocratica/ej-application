import datetime
from datetime import date

from constance import config
from django.conf import settings
from django.urls import reverse
from django.utils.translation import gettext as _
import pytest

from ej_conversations import create_conversation
from ej_conversations.enums import Choice
from ej_conversations.models.comment import Comment
from ej_conversations.models.vote import Vote
from ej_conversations.mommy_recipes import ConversationRecipes
from ej_profiles.enums import Gender, Race
from ej_profiles.models import Profile
from ej_users.models import User


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

    def test_statistics_for_user(self, db, mk_conversation, mk_user):
        conversation = mk_conversation()
        user = mk_user(email="user@domain.com")
        author = mk_user(email="anotherauthor@domain.com")

        comment = conversation.create_comment(
            author, "ad", status="approved", check_limits=False
        )
        comment2 = conversation.create_comment(
            author, "ad2", status="approved", check_limits=False
        )
        comment3 = conversation.create_comment(
            author, "ad3", status="approved", check_limits=False
        )

        comment.vote(user, "agree")
        comment2.vote(user, "disagree")
        comment3.vote(user, "skip")

        statistics_for_user_result = user.profile.conversation_statistics(conversation)

        assert "votes" in statistics_for_user_result
        assert statistics_for_user_result["votes"] == 2

        assert "missing_votes" in statistics_for_user_result
        assert statistics_for_user_result["missing_votes"] == 1

        assert "total_comments" in statistics_for_user_result
        assert statistics_for_user_result["total_comments"] == 3

        assert "comments" in statistics_for_user_result
        assert statistics_for_user_result["comments"] == 2

    def test_statistics_for_user_without_skiped_votes(self, db, mk_conversation, mk_user):
        conversation = mk_conversation()
        user = mk_user(email="user@domain.com")
        author = mk_user(email="anotherauthor@domain.com")

        comment = conversation.create_comment(
            author, "ad", status="approved", check_limits=False
        )
        comment2 = conversation.create_comment(
            author, "ad2", status="approved", check_limits=False
        )
        comment3 = conversation.create_comment(
            author, "ad3", status="approved", check_limits=False
        )

        comment.vote(user, "agree")
        comment2.vote(user, "disagree")
        comment3.vote(user, "skip")

        config.RETURN_USER_SKIPED_COMMENTS = False
        statistics_for_user_result = user.profile.conversation_statistics(conversation)

        assert "votes" in statistics_for_user_result
        assert statistics_for_user_result["votes"] == 3

        assert "missing_votes" in statistics_for_user_result
        assert statistics_for_user_result["missing_votes"] == 0

        assert "total_comments" in statistics_for_user_result
        assert statistics_for_user_result["total_comments"] == 3

        assert "comments" in statistics_for_user_result
        assert statistics_for_user_result["comments"] == 3
