import pytest
from django.utils.translation import gettext_lazy as _

from ej_users.models import User
from ej_conversations.mommy_recipes import ConversationRecipes
from ej_conversations import create_conversation
from ej_conversations.tests.conftest import (
    API_V1_URL,
    ApiClient,
    get_authorized_api_client,
)


class TestGetBoards(ConversationRecipes):
    AUTH_ERROR = {"detail": _("Authentication credentials were not provided.")}

    @pytest.fixture
    def user(db):
        user = User.objects.create_user("email2@server.com", "password")
        user.save()
        return user

    @pytest.fixture
    def conversation_with_board(self, board, user_db):
        board.owner = user_db
        board.save()
        conversation = create_conversation("foo", "conv1", user_db, board=board)
        conversation.board = board
        conversation.save()
        return conversation

    @pytest.mark.django_db
    def test_boards_endpoint(self, user, board, conversation_with_board):
        BOARD = {
            "title": board.title,
            "slug": board.slug,
            "owner": board.owner.email,
            "description": board.description,
            "links": {"self": "http://testserver/api/v1/boards/1/"},
        }

        api = get_authorized_api_client({"email": user.email, "password": "password"})
        path = API_V1_URL + "/boards/"
        result = api.get(path)
        assert result.data.get("results")[0] == BOARD

    def test_boards_endpoint_not_authenticated(self, client, board):
        BOARD = {
            "title": board.title,
            "slug": board.slug,
            "owner": board.owner.email,
            "description": board.description,
            "links": {"self": "http://testserver/api/v1/boards/1/"},
        }
        path = API_V1_URL + "/boards/"
        assert ApiClient(client).get(path, BOARD).data == self.AUTH_ERROR

    @pytest.mark.django_db
    def test_boards_endpoint_with_conversations_list(
        self, user, board, conversation_with_board
    ):
        BOARD = {
            "title": "Title",
            "slug": "board-slug",
            "owner": "user@domain.com",
            "description": "Description",
            "conversations": [
                {
                    "id": 1,
                    "text": "foo",
                    "statistics": {
                        "votes": {"agree": 0, "disagree": 0, "skip": 0, "total": 0},
                        "comments": {
                            "approved": 0,
                            "rejected": 0,
                            "pending": 0,
                            "total": 0,
                        },
                        "participants": {"voters": 0, "commenters": 0},
                        "channel_votes": {
                            "webchat": 0,
                            "telegram": 0,
                            "whatsapp": 0,
                            "opinion_component": 0,
                            "unknown": 0,
                            "ej": 0,
                        },
                        "channel_participants": {
                            "webchat": 0,
                            "telegram": 0,
                            "whatsapp": 0,
                            "opinion_component": 0,
                            "unknown": 0,
                            "ej": 0,
                        },
                    },
                    "participants_can_add_comments": True,
                    "anonymous_votes": 0,
                    "links": {"self": "/api/v1/boards/1/conversations/1/"},
                }
            ],
        }

        api = get_authorized_api_client({"email": user.email, "password": "password"})
        path = API_V1_URL + "/boards/1/"
        result = api.get(path)
        assert result.data == BOARD

    @pytest.mark.django_db
    def test_boards_endpoint_with_conversations_id(
        self, user, board, conversation_with_board
    ):
        CONVERSATION_BOARD = {
            "id": 1,
            "text": "foo",
            "statistics": {
                "votes": {"agree": 0, "disagree": 0, "skip": 0, "total": 0},
                "comments": {
                    "approved": 0,
                    "rejected": 0,
                    "pending": 0,
                    "total": 0,
                },
                "participants": {"voters": 0, "commenters": 0},
                "channel_votes": {
                    "webchat": 0,
                    "telegram": 0,
                    "whatsapp": 0,
                    "opinion_component": 0,
                    "unknown": 0,
                    "ej": 0,
                },
                "channel_participants": {
                    "webchat": 0,
                    "telegram": 0,
                    "whatsapp": 0,
                    "opinion_component": 0,
                    "unknown": 0,
                    "ej": 0,
                },
            },
            "participants_can_add_comments": True,
            "anonymous_votes": 0,
            "links": {"self": "/api/v1/boards/1/conversations/1/"},
        }

        api = get_authorized_api_client({"email": user.email, "password": "password"})
        path = API_V1_URL + "/boards/1/conversations/1/"
        result = api.get(path)
        assert result.data == CONVERSATION_BOARD

    @pytest.mark.django_db
    def test_boards_endpoint_with_invalid_conversations_id(self, user, board):
        api = get_authorized_api_client({"email": user.email, "password": "password"})
        path = API_V1_URL + "/boards/1/conversations/112039012/"
        result = api.get(path)
        assert result.status_code == 404

    @pytest.mark.django_db
    def test_boards_endpoint_with_valid_conversation_id_invalid_board(
        self, user, board, conversation_with_board
    ):
        api = get_authorized_api_client({"email": user.email, "password": "password"})
        path = API_V1_URL + "/boards/1123213/conversations/1/"
        result = api.get(path)
        assert result.status_code == 404
