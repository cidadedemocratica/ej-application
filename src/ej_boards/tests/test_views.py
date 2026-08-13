from django.test import Client
from ej_conversations.mommy_recipes import ConversationRecipes
from ej_users.models import User
from ej_boards.models import Board
from ej_conversations import create_conversation
from ej_conversations.models import Conversation
from django.shortcuts import reverse


class TestBoardsView(ConversationRecipes):
    def test_create_view_renders_breadcrumb_without_side_menu(self, db):
        user = User.objects.create_user("user@email.br", "password")
        client = Client()
        client.force_login(user)

        response = client.get(reverse("boards:board-create"))

        assert response.status_code == 200
        assert b'class="breadcrumb"' in response.content
        assert response.content.count(b'<li class="breadcrumb__item') == 2
        assert b'aria-current="page">Create board' in response.content
        assert b"participant-menu" not in response.content

    def test_edit_view_renders_breadcrumb_without_side_menu(self, db):
        user = User.objects.create_user("user@email.br", "password")
        board = Board.objects.create(
            slug="board", owner=user, description="board"
        )
        client = Client()
        client.force_login(user)

        response = client.get(
            reverse("boards:board-edit", kwargs={"board_slug": board.slug})
        )

        assert response.status_code == 200
        assert b'class="breadcrumb"' in response.content
        assert response.content.count(b'<li class="breadcrumb__item') == 3
        assert b">Board<" in response.content
        assert b'aria-current="page">Settings' in response.content
        assert b"participant-menu" not in response.content

    def test_owner_can_delete_board(self, db):
        user = User.objects.create_user("user@email.br", "password")
        board = Board.objects.create(
            slug="board", owner=user, description="board"
        )
        create_conversation("foo", "conv1", user, board=board)

        client = Client()
        client.login(email="user@email.br", password="password")

        delete_board_url = reverse(
            "boards:board-delete", kwargs={"board_slug": board.slug}
        )
        assert user.boards.count() == 2

        client.post(delete_board_url)

        assert user.boards.count() == 1
        assert not Conversation.objects.filter(title="conv1").exists()

    def test_board_can_only_be_deleted_by_owner(self, db):
        user = User.objects.create_user("user@email.br", "password")
        board = Board.objects.create(
            slug="board", owner=user, description="board"
        )
        create_conversation("foo", "conv1", user, board=board)

        user = User.objects.create_user("second_user@email.br", "password")
        client = Client()
        client.login(email="second_user@email.br", password="password")

        delete_board_url = reverse(
            "boards:board-delete", kwargs={"board_slug": board.slug}
        )

        client.post(delete_board_url)

        assert Board.objects.filter(slug="board").exists()
        assert Conversation.objects.filter(title="conv1").exists()

    def test_board_should_not_be_deleted_when_there_is_only_one_board(self, db):
        user = User.objects.create_user("user_tester@email.br", "password")
        board = Board.objects.create(
            slug="board", owner=user, description="board"
        )
        create_conversation("foo", "conv1", user, board=board)

        client = Client()
        client.login(email="user_tester@email.br", password="password")

        delete_board_url = reverse(
            "boards:board-delete", kwargs={"board_slug": board.slug}
        )

        assert user.boards.count() == 2

        client.post(delete_board_url)

        assert user.boards.count() == 1

        delete_board_url = reverse(
            "boards:board-delete",
            kwargs={"board_slug": user.boards.first().slug},
        )

        assert user.boards.count() == 1
