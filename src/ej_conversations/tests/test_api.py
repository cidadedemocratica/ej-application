import pytest
from django.utils.translation import gettext_lazy as _
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

from ej_conversations.models import Comment, Vote
from ej_conversations.roles.comments import comment_summary
from ej_conversations.models.util import vote_count, statistics_for_user, statistics
from ej_conversations.mommy_recipes import ConversationRecipes
from ej_conversations.enums import Choice
from ej_conversations.models.vote import VoteChannels
from ej_boards.models import Board
from ej_users.models import User
from .examples import COMMENT, CONVERSATION, VOTE, VOTES

BASE_URL = "/api/v1"


@pytest.fixture
def admin_user(db):
    admin_user = User.objects.create_superuser("admin@test.com", "pass")
    admin_user.save()
    return admin_user


@pytest.fixture
def other_user(db):
    user = User.objects.create_user("email2@server.com", "password")
    user.save()
    return user


def authenticate_user_api(user_info):
    api = APIClient()
    response = api.post(BASE_URL + "/login/", user_info, format="json")
    user_token = response.json()["token"]
    api.credentials(HTTP_AUTHORIZATION="Token " + user_token)
    return api


class TestGetViews:
    def test_conversations_endpoint_author(self, conversation):
        path = BASE_URL + f"/conversations/{conversation.id}/"
        api = authenticate_user_api({"email": "email@server.com", "password": "password"})

        data = api.get(path, format="json").data
        del data["created"]
        assert data == CONVERSATION

    def test_conversations_endpoint_admin(self, conversation, admin_user):
        path = BASE_URL + f"/conversations/{conversation.id}/"
        api = authenticate_user_api({"email": admin_user.email, "password": "pass"})

        data = api.get(path, format="json").data
        del data["created"]
        assert data == CONVERSATION

    def test_conversations_endpoint_not_authenticated(self, conversation, api):
        path = BASE_URL + f"/conversations/{conversation.id}/"
        data = api.get(path)
        assert len(data) == 2
        assert data.get("text") == conversation.text
        assert data.get("statistics")

    def test_conversations_endpoint_other_user(self, conversation, other_user):
        path = BASE_URL + f"/conversations/{conversation.id}/"
        api = authenticate_user_api({"email": other_user.email, "password": "password"})

        data = api.get(path, format="json").data
        assert len(data) == 2
        assert data.get("text") == conversation.text
        assert data.get("statistics")

    def test_comments_endpoint(self, comment):
        path = BASE_URL + f"/comments/{comment.id}/"
        api = authenticate_user_api({"email": "email@server.com", "password": "password"})

        data = api.get(path, format="json").data
        del data["created"]
        assert data == COMMENT

    def test_comments_endpoint_user_is_author(self, comment):
        path = BASE_URL + f"/comments/?is_author=true"
        api = authenticate_user_api({"email": "email@server.com", "password": "password"})
        data = api.get(path, format="json").data

        assert data[0]["summary"] == comment_summary(comment)

    def test_comments_endpoint_is_approved(self, comment):
        path = BASE_URL + f"/comments/?is_author=true&is_approved=true"
        api = authenticate_user_api({"email": "email@server.com", "password": "password"})
        data = api.get(path, format="json").data

        assert data[0]["summary"] == comment_summary(comment)

    def test_comments_endpoint_is_rejected(self, comment):
        path = BASE_URL + f"/comments/?is_author=true&is_rejected=true"
        comment.status = "rejected"
        comment.save()
        api = authenticate_user_api({"email": "email@server.com", "password": "password"})
        data = api.get(path, format="json").data

        assert data[0]["summary"] == comment_summary(comment)

    def test_comments_endpoint_is_pending(self, comment):
        path = BASE_URL + f"/comments/?is_author=true&is_pending=true"
        comment.status = "pending"
        comment.save()
        api = authenticate_user_api({"email": "email@server.com", "password": "password"})
        data = api.get(path, format="json").data

        assert data[0]["summary"] == comment_summary(comment)

    def test_comments_endpoint_is_pending_is_approved_combination(self, comments):
        path = BASE_URL + f"/comments/?is_author=true&is_pending=true&is_approved=true"
        pending_comment = comments[0]
        pending_comment.status = "pending"
        pending_comment.save()
        api = authenticate_user_api({"email": "email@server.com", "password": "password"})
        data = api.get(path, format="json").data

        assert data[0]["summary"] == comment_summary(pending_comment)
        assert data[1]["summary"] == comment_summary(comments[1])

    def test_random_comments_endpoint(self, comment):
        path = BASE_URL + f"/conversations/{comment.conversation.id}/random-comment/"
        api = authenticate_user_api({"email": "email@server.com", "password": "password"})
        data = api.get(path, format="json").data
        del data["created"]
        assert data

    def test_random_comment_with_id_endpoint(self, comments):
        comment = comments[1]
        path = BASE_URL + f"/conversations/{comment.conversation.id}/random-comment/?id={comment.id}"
        api = authenticate_user_api({"email": "email@server.com", "password": "password"})
        data = api.get(path, format="json").data
        assert data["content"] == comment.content

    def test_random_voted_comment_with_id_endpoint(self, comments):
        comment = comments[1]
        voting_path = BASE_URL + f"/votes/"
        post_data = {
            "choice": 1,
            "comment": comment.id,
            "channel": "telegram",
        }
        api = authenticate_user_api({"email": "email@server.com", "password": "password"})
        api.post(voting_path, post_data)

        comment_path = (
            BASE_URL + f"/conversations/{comment.conversation.id}/random-comment/?id={comment.id}"
        )
        data = api.get(comment_path, format="json").data
        # random-comment route should never return an voted comment, even if id is present.
        assert data["content"] != comment.content

    def test_get_promoted_conversations(self, conversation):
        path = BASE_URL + f"/conversations/?is_promoted=true"
        api = authenticate_user_api({"email": "email@server.com", "password": "password"})
        data = api.get(path, format="json").data
        assert "card" in data[0]

    def test_search_conversation(self, conversation):
        path = BASE_URL + f"/conversations/?is_promoted=true&text_contains={conversation.text}"
        api = authenticate_user_api({"email": "email@server.com", "password": "password"})
        data = api.get(path, format="json").data
        assert "card" in data[0]

    def test_search_inexistent_conversation(self, conversation):
        path = BASE_URL + f"/conversations/?is_promoted=true&text_contains=asdfghjkl"
        api = authenticate_user_api({"email": "email@server.com", "password": "password"})
        data = api.get(path, format="json").data
        assert data == []

    def test_get_conversation_by_tags(self, conversation):
        tag = "tag"
        conversation.tags.set([tag])
        path = BASE_URL + f"/conversations/?tags={tag}"
        api = authenticate_user_api({"email": "email@server.com", "password": "password"})
        data = api.get(path, format="json").data
        assert "card" in data[0]

    def test_get_vote_endpoint(self, vote):
        path = BASE_URL + f"/votes/{vote.id}/"
        api = authenticate_user_api({"email": "email@server.com", "password": "password"})

        data = api.get(path, format="json").data
        del data["created"]
        assert data == VOTE

    def test_conversation_votes_endpoint_with_anonymous(self, conversation, vote, api):
        path = BASE_URL + f"/conversations/{conversation.id}/votes/"
        api.get(path)
        assert api.response.status_code == 401

    def test_conversation_votes_endpoint(self, conversation, vote, api):
        api = authenticate_user_api({"email": "email@server.com", "password": "password"})
        path = BASE_URL + f"/conversations/{conversation.id}/votes/"
        response = api.get(path, format="json")
        data = response.data
        assert type(data) == list
        assert data[0].get("id") == VOTES[0].get("id")
        assert data[0].get("content") == VOTES[0].get("content")
        assert data[0].get("author__metadata__mautic_id") == VOTES[0].get("author__metadata__mautic_id")
        assert data[0].get("author__metadata__analytics_id") == VOTES[0].get(
            "author__metadata__analytics_id"
        )
        assert data[0].get("comment_id") == VOTES[0].get("comment_id")


class TestApiRoutes:
    AUTH_ERROR = {"detail": _("Authentication credentials were not provided.")}
    EXCLUDES = dict(skip=["created", "modified"])

    def test_post_conversation(self, api, user):
        path = BASE_URL + f"/conversations/"
        board = Board.objects.create(slug="board1", title="My Board", owner=user, description="board")
        post_data = dict(
            title=CONVERSATION["title"], text=CONVERSATION["text"], author=user.id, board=board.id
        )

        # Non authenticated user
        assert api.post(path, post_data) == self.AUTH_ERROR

        # # Authenticated user
        token = Token.objects.create(user=user)
        _api = APIClient()
        _api.credentials(HTTP_AUTHORIZATION="Token " + token.key)
        response = _api.post(path, post_data, format="json")
        assert response.status_code == 403

    def test_delete_conversation(self, user):
        path = BASE_URL + f"/conversations/"
        board = Board.objects.create(slug="board1", title="My Board", owner=user, description="board")
        post_data = dict(
            title=CONVERSATION["title"], text=CONVERSATION["text"], author=user.id, board=board.id
        )

        # Authenticated user
        token = Token.objects.create(user=user)
        _api = APIClient()
        _api.credentials(HTTP_AUTHORIZATION="Token " + token.key)

        # # attempts to create a conversation
        response = _api.post(path, post_data, format="json")
        assert response.status_code == 403

    def test_update_conversation(self, user):
        path = BASE_URL + f"/conversations/"
        board = Board.objects.create(slug="board1", title="My Board", owner=user, description="board")
        post_data = dict(
            title=CONVERSATION["title"], text=CONVERSATION["text"], author=user.id, board=board.id
        )

        # Authenticated user
        token = Token.objects.create(user=user)
        _api = APIClient()
        _api.credentials(HTTP_AUTHORIZATION="Token " + token.key)

        # attempts to create a conversation
        response = _api.post(path, post_data, format="json")
        assert response.status_code == 403

        # attempts to update the conversation
        path = path + "1/"
        response = _api.put(
            path,
            data={"title": "updated title", "text": "updated text"},
            HTTP_AUTHORIZATION=f"Token {token.key}",
        )
        assert response.status_code == 403

    def test_post_comment(self, api, conversation, user):
        comments_path = BASE_URL + f"/comments/"
        comment_data = dict(COMMENT, status="pending")
        post_data = dict(
            content=comment_data["content"],
            conversation=conversation.id,
        )

        # Non authenticated user
        assert api.post(comments_path, post_data) == self.AUTH_ERROR

        # Authenticated user
        token = Token.objects.create(user=user)
        _api = APIClient()
        _api.credentials(HTTP_AUTHORIZATION="Token " + token.key)
        response = _api.post(comments_path, post_data, format="json")
        data = response.data
        del data["created"]
        assert data == comment_data

        # Check if endpoint matches...
        comment = Comment.objects.first()
        auth_token = api.post(BASE_URL + "/login/", {"email": "email@server.com", "password": "password"})
        data = api.client.get(
            comments_path + f"{comment.id}/",
            {},
            HTTP_AUTHORIZATION=f"Token {auth_token.get('token')}",
            format="json",
        ).data

        del data["created"]
        assert data == comment_data

    def test_delete_comment(self, conversation, user):
        comments_path = BASE_URL + f"/comments/"
        comment_data = dict(COMMENT, status="pending")
        post_data = dict(
            content=comment_data["content"],
            conversation=conversation.id,
        )

        # Authenticated user
        token = Token.objects.create(user=user)
        _api = APIClient()
        _api.credentials(HTTP_AUTHORIZATION="Token " + token.key)

        # Creates a comment
        _api.post(comments_path, post_data, format="json")
        comment = Comment.objects.first()
        assert comment

        # delete the comment
        path = comments_path + f"{comment.id}/"
        _api.delete(path, HTTP_AUTHORIZATION=f"Token {token.key}")
        comment = Comment.objects.first()
        assert not comment

    def test_update_comment(self, conversation, user):
        comments_path = BASE_URL + f"/comments/"
        comment_data = dict(COMMENT, status="pending")
        post_data = dict(
            content=comment_data["content"],
            conversation=conversation.id,
        )

        # Authenticated user
        token = Token.objects.create(user=user)
        _api = APIClient()
        _api.credentials(HTTP_AUTHORIZATION="Token " + token.key)

        # Creates a comment
        response = _api.post(comments_path, post_data, format="json")
        data = response.data
        del data["created"]
        assert data == comment_data

        # Updates the comment
        comment = Comment.objects.first()
        path = comments_path + f"{comment.id}/"
        update_data = {
            "content": "updated content",
            "rejection_reason": "10",
            "rejection_reason_text": "updated rejection text",
            "status": "rejected",
        }
        response = _api.put(
            path,
            data=update_data,
            HTTP_AUTHORIZATION=f"Token {token.key}",
        )

        comment = Comment.objects.first()
        assert comment.content == "updated content"
        assert comment.rejection_reason == 10
        assert comment.rejection_reason_text == "updated rejection text"
        assert comment.status == "rejected"

    def test_post_vote(self, api, comment, user):
        path = BASE_URL + f"/votes/"
        post_data = {
            "analytics_utm": {
                "utm_campaign": 1,
                "utm_test": "test",
            },
            "choice": 1,
            "comment": comment.id,
            "channel": "telegram",
        }

        # Non authenticated user
        assert api.post(path, post_data) == self.AUTH_ERROR

        # Authenticated user
        token = Token.objects.create(user=user)
        _api = APIClient()
        _api.credentials(HTTP_AUTHORIZATION="Token " + token.key)
        _api.post(path, post_data, format="json")

        vote = comment.votes.last()

        assert vote.analytics_utm == {"utm_campaign": 1, "utm_test": "test"}

    def test_post_vote_without_analytics_utm(self, api, comment, user):
        path = BASE_URL + f"/votes/"
        post_data = {
            "choice": 0,
            "comment": comment.id,
            "channel": "socketio",
        }

        # Authenticated user
        token = Token.objects.create(user=user)
        _api = APIClient()
        _api.credentials(HTTP_AUTHORIZATION="Token " + token.key)
        _api.post(path, post_data, format="json")

        vote = comment.votes.last()
        assert vote.analytics_utm == None

        post_data["analytics_utm"] = {}
        _api.post(path, post_data, format="json")

        vote = comment.votes.last()
        assert vote.analytics_utm == {}

    def test_post_skipped_vote(self, api, comment, user):
        path = BASE_URL + f"/votes/"
        post_data = {
            "analytics_utm": {
                "utm_campaign": 1,
                "utm_test": "test",
            },
            "choice": 0,
            "comment": comment.id,
            "channel": "telegram",
        }

        # Authenticated user
        token = Token.objects.create(user=user)
        _api = APIClient()
        _api.credentials(HTTP_AUTHORIZATION="Token " + token.key)

        _api.post(path, post_data, format="json")

        post_data = {
            "analytics_utm": {
                "utm_campaign": 2,
            },
            "choice": 1,
            "comment": comment.id,
            "channel": "telegram",
        }

        vote = comment.votes.last()
        assert vote.analytics_utm == {"utm_campaign": 1, "utm_test": "test"}

        _api.post(path, post_data, format="json")

        vote = comment.votes.last()
        assert vote.analytics_utm == {
            "utm_campaign": 2,
        }

    def test_delete_vote(self, comment, user, admin_user, other_user):
        path = BASE_URL + f"/votes/"
        post_data = {
            "analytics_utm": {
                "utm_campaign": 1,
                "utm_test": "test",
            },
            "choice": 0,
            "comment": comment.id,
            "channel": "opinion_component",
        }

        # Authenticated normal user
        token = Token.objects.create(user=user)
        _api = APIClient()
        _api.credentials(HTTP_AUTHORIZATION="Token " + token.key)

        # Creates a vote
        _api.post(path, post_data, format="json")
        vote = Vote.objects.first()
        assert vote

        path = path + f"{vote.id}/"
        response = _api.delete(path, HTTP_AUTHORIZATION=f"Token {token.key}")
        assert response.status_code == 403

        # User try to delete another user vote
        token3 = Token.objects.create(user=other_user)
        _api.credentials(HTTP_AUTHORIZATION="Token " + token3.key)
        response = _api.delete(path, HTTP_AUTHORIZATION=f"Token {token3.key}")
        assert response.status_code == 403

        # Authenticated superuser
        token2 = Token.objects.create(user=admin_user)
        _api.credentials(HTTP_AUTHORIZATION="Token " + token2.key)
        response = _api.delete(path, HTTP_AUTHORIZATION=f"Token {token2.key}")
        assert response.status_code == 204
        vote = Vote.objects.first()
        assert not vote

    def test_update_vote(self, comment, user):
        path = BASE_URL + f"/votes/"
        post_data = {
            "analytics_utm": {
                "utm_campaign": 1,
                "utm_test": "test",
            },
            "choice": 1,
            "comment": comment.id,
            "channel": "telegram",
        }

        # Authenticated user
        token = Token.objects.create(user=user)
        _api = APIClient()
        _api.credentials(HTTP_AUTHORIZATION="Token " + token.key)

        # Creates a vote
        _api.post(path, post_data, format="json")
        vote = Vote.objects.first()
        assert vote

        # Updates the vote
        path = path + f"{vote.id}/"
        update_data = {"choice": "-1", "analytics_utm": {"utm_test": "updated test"}}
        _api.put(
            path,
            data=update_data,
            format="json",
            HTTP_AUTHORIZATION=f"Token {token.key}",
        )

        vote = Vote.objects.first()
        assert vote.analytics_utm == {"utm_test": "updated test"}
        assert vote.choice == Choice.DISAGREE


class TestConversartionStatistics(ConversationRecipes):
    def test_vote_count_of_a_conversation(self, db, mk_conversation, mk_user):
        conversation = mk_conversation()
        vote_count_result = vote_count(conversation)
        assert vote_count_result == 0

        user = mk_user(email="user@domain.com")
        comment = conversation.create_comment(user, "aa", status="approved", check_limits=False)
        comment.vote(user, "agree")
        vote_count_result = vote_count(conversation)
        assert vote_count_result == 1

    def test_vote_count_agree(self, db, mk_conversation, mk_user):
        conversation = mk_conversation()
        user = mk_user(email="user@domain.com")
        vote_count_result = vote_count(conversation, Choice.AGREE)
        assert vote_count_result == 0

        comment = conversation.create_comment(user, "aa", status="approved", check_limits=False)
        comment.vote(user, "agree")
        vote_count_result = vote_count(conversation, Choice.AGREE)
        assert vote_count_result == 1

        other = mk_user(email="other@domain.com")
        comment = conversation.create_comment(user, "ab", status="approved", check_limits=False)
        comment.vote(other, "disagree")
        vote_count_result = vote_count(conversation, Choice.AGREE)
        assert vote_count_result == 1

    def test_vote_count_disagree(self, db, mk_conversation, mk_user):
        conversation = mk_conversation()
        user = mk_user(email="user@domain.com")
        vote_count_result = vote_count(conversation, Choice.DISAGREE)
        assert vote_count_result == 0

        comment = conversation.create_comment(user, "ac", status="approved", check_limits=False)
        comment.vote(user, "disagree")
        vote_count_result = vote_count(conversation, Choice.DISAGREE)
        assert vote_count_result == 1

    def test_vote_count_skip(self, db, mk_conversation, mk_user):
        conversation = mk_conversation()
        user = mk_user(email="user@domain.com")
        vote_count_result = vote_count(conversation, Choice.SKIP)
        assert vote_count_result == 0

        comment = conversation.create_comment(user, "ad", status="approved", check_limits=False)
        comment.vote(user, "skip")
        vote_count_result = vote_count(conversation, Choice.SKIP)
        assert vote_count_result == 1

    def test_statistics_return(self, db, mk_conversation):
        conversation = mk_conversation()
        statistics_result = statistics(conversation)

        assert "votes" in statistics_result
        assert "agree" in statistics_result["votes"]
        assert "disagree" in statistics_result["votes"]
        assert "skip" in statistics_result["votes"]
        assert "total" in statistics_result["votes"]

        assert "comments" in statistics_result
        assert "approved" in statistics_result["comments"]
        assert "rejected" in statistics_result["comments"]
        assert "pending" in statistics_result["comments"]
        assert "total" in statistics_result["comments"]

        assert "participants" in statistics_result
        assert "voters" in statistics_result["participants"]
        assert "commenters" in statistics_result["participants"]

        assert "channel_votes" in statistics_result
        assert "webchat" in statistics_result["channel_votes"]
        assert "telegram" in statistics_result["channel_votes"]
        assert "whatsapp" in statistics_result["channel_votes"]
        assert "opinion_component" in statistics_result["channel_votes"]
        assert "unknown" in statistics_result["channel_votes"]
        assert "ej" in statistics_result["channel_votes"]

        assert "channel_participants" in statistics_result
        assert "webchat" in statistics_result["channel_participants"]
        assert "telegram" in statistics_result["channel_participants"]
        assert "whatsapp" in statistics_result["channel_participants"]
        assert "opinion_component" in statistics_result["channel_participants"]
        assert "unknown" in statistics_result["channel_participants"]
        assert "ej" in statistics_result["channel_participants"]

        assert conversation._cached_statistics == statistics_result

    def test_statistics_for_user(self, db, mk_conversation, mk_user):
        conversation = mk_conversation()
        user = mk_user(email="user@domain.com")
        statistics_for_user_result = statistics_for_user(conversation, user)

        assert "votes" in statistics_for_user_result
        assert "missing_votes" in statistics_for_user_result
        assert "participation_ratio" in statistics_for_user_result
        assert "total_comments" in statistics_for_user_result
        assert "comments" in statistics_for_user_result

    def test_statistics_for_channel_votes(self, db, mk_conversation, mk_user):
        conversation = mk_conversation()
        user1 = mk_user(email="user1@domain.com")
        user2 = mk_user(email="user2@domain.com")
        user3 = mk_user(email="user3@domain.com")
        comment = conversation.create_comment(user1, "ad", status="approved", check_limits=False)
        comment2 = conversation.create_comment(user1, "ad2", status="approved", check_limits=False)
        comment3 = conversation.create_comment(user2, "ad3", status="approved", check_limits=False)

        vote = comment.vote(user1, Choice.AGREE)
        vote.channel = VoteChannels.TELEGRAM
        vote.save()

        vote = comment.vote(user2, Choice.AGREE)
        vote.channel = VoteChannels.WHATSAPP
        vote.save()

        vote = comment.vote(user3, Choice.AGREE)
        vote.channel = VoteChannels.WHATSAPP
        vote.save()

        vote = comment2.vote(user1, Choice.AGREE)
        vote.channel = VoteChannels.OPINION_COMPONENT
        vote.save()

        vote = comment2.vote(user2, Choice.AGREE)
        vote.channel = VoteChannels.RASA_WEBCHAT
        vote.save()

        vote = comment2.vote(user3, Choice.AGREE)
        vote.channel = VoteChannels.UNKNOWN
        vote.save()

        vote = comment3.vote(user3, Choice.AGREE)
        vote.channel = VoteChannels.EJ
        vote.save()

        statistics = conversation.statistics()
        assert statistics["channel_votes"]["telegram"] == 1
        assert statistics["channel_votes"]["whatsapp"] == 2
        assert statistics["channel_votes"]["opinion_component"] == 1
        assert statistics["channel_votes"]["webchat"] == 1
        assert statistics["channel_votes"]["unknown"] == 1
        assert statistics["channel_votes"]["ej"] == 1

    def test_statistics_for_channel_participants(self, db, mk_conversation, mk_user):
        conversation = mk_conversation()
        user1 = mk_user(email="user1@domain.com")
        user2 = mk_user(email="user2@domain.com")
        user3 = mk_user(email="user3@domain.com")

        comment = conversation.create_comment(user1, "ad", status="approved", check_limits=False)
        comment2 = conversation.create_comment(user1, "ad2", status="approved", check_limits=False)
        comment3 = conversation.create_comment(user2, "ad3", status="approved", check_limits=False)

        # 3 participantes pelo telegram
        vote = comment.vote(user1, Choice.AGREE)
        vote.channel = VoteChannels.TELEGRAM
        vote.save()

        vote = comment.vote(user2, Choice.AGREE)
        vote.channel = VoteChannels.TELEGRAM
        vote.save()

        vote = comment.vote(user3, Choice.AGREE)
        vote.channel = VoteChannels.TELEGRAM
        vote.save()

        vote = comment2.vote(user1, Choice.AGREE)
        vote.channel = VoteChannels.TELEGRAM
        vote.save()

        vote = comment2.vote(user2, Choice.AGREE)
        vote.channel = VoteChannels.OPINION_COMPONENT
        vote.save()

        vote = comment2.vote(user3, Choice.AGREE)
        vote.channel = VoteChannels.UNKNOWN
        vote.save()

        vote = comment3.vote(user1, Choice.AGREE)
        vote.channel = VoteChannels.RASA_WEBCHAT
        vote.save()

        vote = comment3.vote(user2, Choice.AGREE)
        vote.channel = VoteChannels.WHATSAPP
        vote.save()

        vote = comment3.vote(user3, Choice.AGREE)
        vote.channel = VoteChannels.OPINION_COMPONENT
        vote.save()

        statistics = conversation.statistics()
        assert statistics["channel_participants"]["telegram"] == 3
        assert statistics["channel_participants"]["whatsapp"] == 1
        assert statistics["channel_participants"]["opinion_component"] == 2
        assert statistics["channel_participants"]["webchat"] == 1
        assert statistics["channel_participants"]["unknown"] == 1
