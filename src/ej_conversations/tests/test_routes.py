from django.urls import reverse
import json
from ej_conversations.mommy_recipes import ConversationRecipes
from ej.testing import UrlTester
from ej_users.models import User
from ej_boards.models import Board


TEST_DOMAIN = "https://domain.com.br"


class TestRoutes(UrlTester, ConversationRecipes):
    public_urls = ["/conversations/"]
    user_urls = [
        "/boards/board-slug/conversations/1/conversation/",
    ]
    admin_urls = ["/boards/board-slug/conversations/add/"]
    owner_urls = [
        "/boards/board-slug/conversations/1/conversation/edit/",
        "/boards/board-slug/conversations/1/conversation/moderate/",
    ]

    def get_data(self, request):
        conversation = request.getfixturevalue("conversation")
        try:
            board = request.getfixturevalue("board")
            board.owner = request.getfixturevalue("author_db")
            conversation.board = board
            conversation.author = board.owner
            conversation.is_promoted = True
            board.save()
            conversation.save()
        except Exception:
            pass

    def test_add_favorite_board(self, admin_client, root_db):
        user = User.objects.create_user("user1@email.br", "password")
        board_1 = Board.objects.create(slug="board1", owner=user, description="board")
        board_2 = Board.objects.create(slug="board2", owner=root_db, description="board2")

        base_url = reverse(
            "boards:conversation-update-favorite-boards", args=[board_1.slug]
        )
        url = f"{base_url}?updateOption=add"
        admin_client.get(url)

        base_url = reverse(
            "boards:conversation-update-favorite-boards", args=[board_2.slug]
        )
        url = f"{base_url}?updateOption=add"
        admin_client.get(url)

        assert root_db.favorite_boards.get(id=board_1.id) == board_1
        assert root_db.favorite_boards.get(id=board_2.id) == board_2
        assert root_db.favorite_boards.count() == 2

    def test_remove_favorite_board(self, admin_client, root_db):
        user = User.objects.create_user("user1@email.br", "password")
        board_1 = Board.objects.create(slug="board1", owner=user, description="board")
        board_2 = Board.objects.create(slug="board2", owner=root_db, description="board2")

        root_db.favorite_boards.add(board_1)
        root_db.favorite_boards.add(board_2)

        assert root_db.favorite_boards.count() == 2

        base_url = reverse(
            "boards:conversation-update-favorite-boards", args=[board_1.slug]
        )
        url = f"{base_url}?updateOption=remove"
        admin_client.get(url)

        base_url = reverse(
            "boards:conversation-update-favorite-boards", args=[board_2.slug]
        )
        url = f"{base_url}?updateOption=remove"
        admin_client.get(url)

        assert root_db.favorite_boards.count() == 0

    def test_board_is_favorite(self, admin_client, root_db):
        user = User.objects.create_user("user1@email.br", "password")
        board_1 = Board.objects.create(slug="board1", owner=user, description="board")
        board_2 = Board.objects.create(slug="board2", owner=root_db, description="board2")

        root_db.favorite_boards.add(board_1)

        url = reverse("boards:conversation-is-favorite-board", args=[board_1.slug])
        response = admin_client.get(url)
        response_json = json.loads(response.content)
        assert response_json["is_favorite_board"]

        url = reverse("boards:conversation-is-favorite-board", args=[board_2.slug])
        response = admin_client.get(url)
        response_json = json.loads(response.content)
        assert not response_json["is_favorite_board"]
