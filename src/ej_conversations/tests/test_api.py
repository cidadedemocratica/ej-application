import pytest
from django.utils.translation import gettext_lazy as _
from rest_framework.viewsets import reverse

from ej_boards.models import Board
from ej_conversations.enums import Choice
from ej_conversations.models import Comment, Vote
from ej_conversations.roles.comments import comment_summary
from ej_conversations.tests.conftest import API_V1_URL, get_authorized_api_client
from ej_users.models import User

from .examples import COMMENT, CONVERSATION, VOTE, VOTES


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


class TestGetViews:
    def test_conversations_endpoint_author(self, conversation):
        api = get_authorized_api_client(
            {"email": "email@server.com", "password": "password"}
        )
        path = reverse("v1-conversations-detail", kwargs={"pk": conversation.id})
        data = api.get(path, format="json").data
        del data["created"]
        assert data == CONVERSATION

    def test_conversations_endpoint_admin(self, conversation, admin_user):
        api = get_authorized_api_client({"email": admin_user.email, "password": "pass"})

        path = reverse("v1-conversations-detail", kwargs={"pk": conversation.id})
        data = api.get(path, format="json").data
        del data["created"]
        assert data == CONVERSATION

    def test_anonymous_conversations_endpoint(self, conversation, api):
        path = reverse("v1-conversations-detail", kwargs={"pk": conversation.id})
        data = api.get(path)
        assert len(data) == 6
        assert data.get("text") == conversation.text
        assert data.get("statistics")
        assert "participants_can_add_comments" in data.keys()
        assert "anonymous_votes" in data.keys()
        assert "send_profile_question" in data.keys()
        assert "votes_to_send_profile_question" in data.keys()

    def test_authenticated_conversations_endpoint(self, conversation, other_user):
        path = reverse("v1-conversations-detail", kwargs={"pk": conversation.id})
        api = get_authorized_api_client(
            {"email": other_user.email, "password": "password"}
        )

        data = api.get(path, format="json").data
        assert len(data) == 6
        assert data.get("text") == conversation.text
        assert data.get("statistics")
        assert "participants_can_add_comments" in data.keys()
        assert "anonymous_votes" in data.keys()
        assert "send_profile_question" in data.keys()
        assert "votes_to_send_profile_question" in data.keys()

    def test_comments_endpoint(self, comment):
        path = reverse("v1-comments-detail", kwargs={"pk": comment.id})
        api = get_authorized_api_client(
            {"email": "email@server.com", "password": "password"}
        )

        data = api.get(path, format="json").data
        del data["created"]
        assert data == COMMENT

    def test_comments_endpoint_user_is_author(self, comment):
        path = reverse("v1-comments-list")
        api = get_authorized_api_client(
            {"email": "email@server.com", "password": "password"}
        )
        data = api.get(f"{path}?is_author=true", format="json").data

        assert data[0]["summary"] == comment_summary(comment)

    def test_comments_endpoint_is_approved(self, comment):
        path = reverse("v1-comments-list")
        api = get_authorized_api_client(
            {"email": "email@server.com", "password": "password"}
        )
        data = api.get(f"{path}?is_author=true&is_approved=true", format="json").data

        assert data[0]["summary"] == comment_summary(comment)

    def test_comments_endpoint_is_rejected(self, comment):
        path = reverse("v1-comments-list")
        comment.status = "rejected"
        comment.save()
        api = get_authorized_api_client(
            {"email": "email@server.com", "password": "password"}
        )
        data = api.get(f"{path}?is_author=true&is_rejected=true", format="json").data

        assert data[0]["summary"] == comment_summary(comment)

    def test_comments_endpoint_is_pending(self, comment):
        path = reverse("v1-comments-list")
        comment.status = "pending"
        comment.save()
        api = get_authorized_api_client(
            {"email": "email@server.com", "password": "password"}
        )
        data = api.get(f"{path}?is_author=true&is_pending=true", format="json").data

        assert data[0]["summary"] == comment_summary(comment)

    def test_comments_endpoint_is_pending_is_approved_combination(self, comments):
        path = f"{reverse('v1-comments-list')}?is_author=true&is_pending=true&is_approved=true"
        pending_comment = comments[0]
        pending_comment.status = "pending"
        pending_comment.save()
        api = get_authorized_api_client(
            {"email": "email@server.com", "password": "password"}
        )
        data = api.get(path, format="json").data

        assert data[0]["summary"] == comment_summary(pending_comment)
        assert data[1]["summary"] == comment_summary(comments[1])

    def test_random_comments_endpoint(self, comment):
        path = f"{reverse('v1-conversations-random-comment', kwargs={'pk': comment.conversation.id})}?is_author=true&is_pending=true&is_approved=true"
        api = get_authorized_api_client(
            {"email": "email@server.com", "password": "password"}
        )
        data = api.get(path, format="json").data
        del data["created"]
        assert data

    def test_unauthenticated_random_comments_endpoint(self, comment, api_client):
        conversation = comment.conversation
        # TODO: use the reverse util method instead of API_V1_URL constant
        path = API_V1_URL + f"/conversations/{conversation.id}/random-comment/"
        data = api_client.get(path, format="json").data
        assert data["content"] == conversation.approved_comments.first().content

    def test_random_comment_with_id_endpoint(self, comments):
        comment = comments[1]
        # TODO: use the reverse util method instead of API_V1_URL constant
        path = (
            API_V1_URL
            + f"/conversations/{comment.conversation.id}/random-comment/?id={comment.id}"
        )
        api = get_authorized_api_client(
            {"email": "email@server.com", "password": "password"}
        )
        data = api.get(path, format="json").data
        assert data["content"] == comment.content

    def test_random_voted_comment_with_id_endpoint(self, comments):
        comment = comments[1]
        # TODO: use the reverse util method instead of API_V1_URL constant
        voting_path = API_V1_URL + "/votes/"
        post_data = {
            "choice": 1,
            "comment": comment.id,
            "channel": "telegram",
        }
        api = get_authorized_api_client(
            {"email": "email@server.com", "password": "password"}
        )
        api.post(voting_path, post_data)

        # TODO: use the reverse util method instead of API_V1_URL constant
        comment_path = (
            API_V1_URL
            + f"/conversations/{comment.conversation.id}/random-comment/?id={comment.id}"
        )
        data = api.get(comment_path, format="json").data
        # random-comment route should never return an voted comment, even if id is present.
        assert data["content"] != comment.content

    def test_get_promoted_conversations(self, conversation):
        # TODO: use the reverse util method instead of API_V1_URL constant
        path = API_V1_URL + "/conversations/?is_promoted=true"
        api = get_authorized_api_client(
            {"email": "email@server.com", "password": "password"}
        )
        expected_data = {
            "url": conversation.get_absolute_url(),
            "title": "title",
            "text": "test",
            "author": "email@server.com",
            "is_hidden": False,
            "first_tag": None,
            "n_approved_comments": 0,
            "n_final_votes": 0,
            "n_favorites": 0,
            "button_text": "Participate",
        }

        data = api.get(path).data
        assert expected_data == data[0]

    def test_search_conversation(self, conversation):
        # TODO: use the reverse util method instead of API_V1_URL constant
        path = (
            API_V1_URL
            + f"/conversations/?is_promoted=true&search_text={conversation.text}"
        )
        api = get_authorized_api_client(
            {"email": "email@server.com", "password": "password"}
        )

        expected_data = {
            "url": conversation.get_absolute_url(),
            "title": "title",
            "text": "test",
            "author": "email@server.com",
            "is_hidden": False,
            "first_tag": None,
            "n_approved_comments": 0,
            "n_final_votes": 0,
            "n_favorites": 0,
            "button_text": "Participate",
        }

        data = api.get(path).data
        assert expected_data == data[0]

    def test_search_inexistent_conversation(self, conversation):
        # TODO: use the reverse util method instead of API_V1_URL constant
        path = API_V1_URL + "/conversations/?is_promoted=true&search_text=asdfghjkl"
        api = get_authorized_api_client(
            {"email": "email@server.com", "password": "password"}
        )
        data = api.get(path).data
        assert data == []

    def test_get_conversation_by_tags(self, conversation):
        tag = "tag"
        conversation.tags.set([tag])
        # TODO: use the reverse util method instead of API_V1_URL constant
        path = API_V1_URL + f"/conversations/?tags={tag}"
        api = get_authorized_api_client(
            {"email": "email@server.com", "password": "password"}
        )

        expected_data = {
            "url": conversation.get_absolute_url(),
            "title": "title",
            "text": "test",
            "author": "email@server.com",
            "is_hidden": False,
            "first_tag": "tag",
            "n_approved_comments": 0,
            "n_final_votes": 0,
            "n_favorites": 0,
            "button_text": "Participate",
        }

        data = api.get(path).data
        assert expected_data == data[0]

    def test_search_tag_in_search_text(self, conversation):
        tag = "tag"
        conversation.tags.set([tag])
        path = API_V1_URL + f"/conversations/?is_promoted=true&search_text={tag}"
        api = get_authorized_api_client(
            {"email": "email@server.com", "password": "password"}
        )

        expected_data = {
            "url": conversation.get_absolute_url(),
            "title": "title",
            "text": "test",
            "author": "email@server.com",
            "is_hidden": False,
            "first_tag": "tag",
            "n_approved_comments": 0,
            "n_final_votes": 0,
            "n_favorites": 0,
            "button_text": "Participate",
        }

        data = api.get(path).data
        assert expected_data == data[0]

    def test_get_vote_endpoint(self, vote):
        # TODO: use the reverse util method instead of API_V1_URL constant
        path = API_V1_URL + f"/votes/{vote.id}/"
        api = get_authorized_api_client(
            {"email": "email@server.com", "password": "password"}
        )

        data = api.get(path, format="json").data
        del data["created"]
        assert data == VOTE

    def test_conversation_votes_endpoint_with_anonymous(self, conversation, vote, api):
        # TODO: use the reverse util method instead of API_V1_URL constant
        path = API_V1_URL + f"/conversations/{conversation.id}/votes/"
        api.get(path)
        assert api.response.status_code == 401

    def test_conversation_votes_endpoint(self, conversation, vote, api):
        api = get_authorized_api_client(
            {"email": "email@server.com", "password": "password"}
        )
        # TODO: use the reverse util method instead of API_V1_URL constant
        path = API_V1_URL + f"/conversations/{conversation.id}/votes/"
        response = api.get(path, format="json")
        data = response.data
        assert isinstance(data, list)
        assert data[0].get("id") == VOTES[0].get("id")
        assert data[0].get("content") == VOTES[0].get("content")
        assert data[0].get("comment_id") == VOTES[0].get("comment_id")


class TestApiRoutes:
    AUTH_ERROR = {"detail": _("Authentication credentials were not provided.")}
    EXCLUDES = dict(skip=["created", "modified"])

    def test_post_conversation(self, api, user):
        # TODO: use the reverse util method instead of API_V1_URL constant
        path = API_V1_URL + "/conversations/"
        board = Board.objects.create(
            slug="board1", title="Explore", owner=user, description="board"
        )
        post_data = dict(
            title=CONVERSATION["title"],
            text=CONVERSATION["text"],
            author=user.id,
            board=board.id,
        )

        # Non authenticated user
        assert api.post(path, post_data) == self.AUTH_ERROR

        # # Authenticated user
        api = get_authorized_api_client({"email": user.email, "password": "password"})
        response = api.post(path, post_data, format="json")
        assert response.status_code == 403

    def test_delete_conversation(self, user):
        # TODO: use the reverse util method instead of API_V1_URL constant
        path = API_V1_URL + "/conversations/"
        board = Board.objects.create(
            slug="board1", title="Explore", owner=user, description="board"
        )
        post_data = dict(
            title=CONVERSATION["title"],
            text=CONVERSATION["text"],
            author=user.id,
            board=board.id,
        )

        # Authenticated user
        api = get_authorized_api_client({"email": user.email, "password": "password"})

        # # attempts to create a conversation
        response = api.post(path, post_data, format="json")
        assert response.status_code == 403

    def test_update_conversation(self, user):
        # TODO: use the reverse util method instead of API_V1_URL constant
        path = API_V1_URL + "/conversations/"
        board = Board.objects.create(
            slug="board1", title="Explore", owner=user, description="board"
        )
        post_data = dict(
            title=CONVERSATION["title"],
            text=CONVERSATION["text"],
            author=user.id,
            board=board.id,
        )

        # Authenticated user
        api = get_authorized_api_client({"email": user.email, "password": "password"})

        # attempts to create a conversation
        response = api.post(path, post_data, format="json")
        assert response.status_code == 403

        # attempts to update the conversation
        path = path + "1/"
        response = api.put(
            path,
            data={"title": "updated title", "text": "updated text"},
        )
        assert response.status_code == 403

    def test_post_comment(self, api, conversation, user):
        # TODO: use the reverse util method instead of API_V1_URL constant
        comments_path = API_V1_URL + "/comments/"
        comment_data = dict(COMMENT, status="pending")
        post_data = dict(
            content=comment_data["content"],
            conversation=conversation.id,
        )

        # Non authenticated user
        assert api.post(comments_path, post_data) == self.AUTH_ERROR

        # Authenticated user
        api = get_authorized_api_client({"email": user.email, "password": "password"})
        response = api.post(comments_path, post_data, format="json")

        data = response.data
        del data["created"]
        assert data == comment_data

        # Check if endpoint matches...
        comment = Comment.objects.first()
        # TODO: use the reverse util method instead of API_V1_URL constant
        api.post(
            API_V1_URL + "/login/", {"email": "email@server.com", "password": "password"}
        )
        data = api.get(
            comments_path + f"{comment.id}/",
            {},
            format="json",
        ).data

        del data["created"]
        assert data == comment_data

    def test_post_comment_with_disabled_option(self, api, conversation, user):
        # TODO: use the reverse util method instead of API_V1_URL constant
        comments_path = API_V1_URL + "/comments/"
        comment_data = dict(COMMENT, status="pending")
        conversation.participants_can_add_comments = False
        conversation.save()
        post_data = dict(
            content=comment_data["content"],
            conversation=conversation.id,
        )

        # Authenticated user
        api = get_authorized_api_client({"email": user.email, "password": "password"})
        response = api.post(comments_path, post_data, format="json")
        assert response.status_code == 403

    def test_delete_comment(self, conversation, user):
        # TODO: use the reverse util method instead of API_V1_URL constant
        comments_path = API_V1_URL + "/comments/"
        comment_data = dict(COMMENT, status="pending")
        post_data = dict(
            content=comment_data["content"],
            conversation=conversation.id,
        )

        # Authenticated user
        api = get_authorized_api_client({"email": user.email, "password": "password"})

        # Creates a comment
        api.post(comments_path, post_data, format="json")
        comment = Comment.objects.first()
        assert comment

        # delete the comment
        path = comments_path + f"{comment.id}/"
        api.delete(path)

        comment = Comment.objects.first()
        assert not comment

    def test_update_comment(self, conversation, user):
        # TODO: use the reverse util method instead of API_V1_URL constant
        comments_path = API_V1_URL + "/comments/"
        comment_data = dict(COMMENT, status="pending")
        post_data = dict(
            content=comment_data["content"],
            conversation=conversation.id,
        )

        # Authenticated user
        api = get_authorized_api_client({"email": user.email, "password": "password"})

        # Creates a comment
        response = api.post(comments_path, post_data, format="json")
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
        response = api.put(
            path,
            data=update_data,
        )

        comment = Comment.objects.first()
        assert comment.content == "updated content"
        assert comment.rejection_reason == 10
        assert comment.rejection_reason_text == "updated rejection text"
        assert comment.status == "rejected"

    def test_post_vote(self, api, comment, user):
        # TODO: use the reverse util method instead of API_V1_URL constant
        path = API_V1_URL + "/votes/"
        post_data = {
            "choice": 0,
            "comment": comment.id,
            "channel": "socketio",
        }

        # Authenticated user
        api = get_authorized_api_client({"email": user.email, "password": "password"})

        api.post(path, post_data, format="json")
        vote = comment.votes.last()
        assert vote

    def test_post_skipped_vote(self, api, comment, user):
        # TODO: use the reverse util method instead of API_V1_URL constant
        path = API_V1_URL + "/votes/"
        post_data = {
            "choice": 0,
            "comment": comment.id,
            "channel": "telegram",
        }

        # Authenticated user
        api = get_authorized_api_client({"email": user.email, "password": "password"})

        api.post(path, post_data, format="json")

        post_data = {
            "choice": 1,
            "comment": comment.id,
            "channel": "telegram",
        }

        vote = comment.votes.last()

        api.post(path, post_data, format="json")

        vote = comment.votes.last()
        assert vote

    def test_update_vote(self, comment, user):
        # TODO: use the reverse util method instead of API_V1_URL constant
        path = API_V1_URL + "/votes/"
        post_data = {
            "choice": 1,
            "comment": comment.id,
            "channel": "telegram",
        }

        # Authenticated user
        api = get_authorized_api_client({"email": user.email, "password": "password"})

        # Creates a vote
        api.post(path, post_data, format="json")
        vote = Vote.objects.first()
        assert vote

        # Updates the vote
        path = path + f"{vote.id}/"
        update_data = {"choice": "-1"}
        api.put(
            path,
            data=update_data,
            format="json",
        )

        vote = Vote.objects.first()
        assert vote.choice == Choice.DISAGREE
