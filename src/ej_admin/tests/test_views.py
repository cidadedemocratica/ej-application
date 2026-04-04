import pytest
from django.test import Client
from ej_users.models import User
from ej_boards.models import Board
from ej_conversations.mommy_recipes import ConversationRecipes
from ej_conversations import create_conversation


class TestAdministration(ConversationRecipes):
    @pytest.fixture
    def admin_user(self, db):
        admin_user = User.objects.create_superuser("admin@test.com", "pass")
        admin_user.save()
        return admin_user

    @pytest.fixture
    def logged_admin(self, admin_user):
        client = Client()
        client.force_login(admin_user)
        return client

    def test_get_environment_statistics(self, logged_admin):
        url = "/administration/"

        user = User.objects.create_user("user1@email.br", "password")
        board = Board.objects.create(
            slug="board1", owner=user, description="board"
        )
        create_conversation("foo", "conv1", user, board=board)

        response = logged_admin.get(url)
        users_count = response.context["users_count"]
        boards_count = response.context["boards_count"]
        conversations_count = response.context["conversations_count"]

        assert users_count == 2
        assert boards_count == 2
        assert conversations_count == 1

    def test_get_active_recent_boards(self, db, logged_admin):
        user = User.objects.create_user("user1@email.br", "password")
        board = Board.objects.create(
            slug="board1", owner=user, description="board"
        )
        board_2 = Board.objects.create(
            slug="board2", owner=user, description="board2"
        )
        Board.objects.create(slug="board3", owner=user, description="board3")

        create_conversation("foo", "conv1", user, board=board)
        create_conversation("foo2", "conv2", user, board=board_2)

        url = "/administration/recent-boards/?boardIsActive=true"

        response = logged_admin.get(url)

        recent_boards = response.context["recent_boards"]
        assert len(recent_boards) == 2
        assert recent_boards[0].slug == "board2"
        assert recent_boards[1].slug == "board1"

    def test_get_all_recent_boards(self, db, logged_admin):
        user = User.objects.create_user("user1@email.br", "password")
        board = Board.objects.create(
            slug="board1", owner=user, description="board"
        )
        board_2 = Board.objects.create(
            slug="board2", owner=user, description="board2"
        )
        Board.objects.create(slug="board3", owner=user, description="board3")

        create_conversation("foo", "conv1", user, board=board)
        create_conversation("foo2", "conv2", user, board=board_2)

        url = "/administration/recent-boards/?boardIsActive=false"

        response = logged_admin.get(url)

        recent_boards = response.context["recent_boards"]
        assert len(recent_boards) == 4
        assert recent_boards[0].slug == "board3"
        assert recent_boards[1].slug == "board2"
        assert recent_boards[2].slug == "board1"
        assert recent_boards[3].slug == "admintestcom"

    def test_get_searched_users_by_date(self, logged_admin, admin_user):
        base_url = "/administration/searched-users/"
        user = User.objects.create_user("user1@email.br", "password")
        url = (
            base_url
            + "?page=1&numEntries=6&orderBy=date&sort=desc&searchString="
        )
        response = logged_admin.get(url)
        searched_users = response.context["page_object"]
        assert len(searched_users) == 2
        assert searched_users[0].email == user.email
        assert searched_users[1].email == admin_user.email

    def test_get_searched_users_by_conversations_count(
        self, logged_admin, admin_user
    ):
        base_url = "/administration/searched-users/"
        url = (
            base_url
            + "?page=1&numEntries=6&orderBy=conversations-count&sort=desc&searchString="
        )

        user = User.objects.create_user("user1@email.br", "password")
        board = Board.objects.create(
            slug="board1", owner=user, description="board"
        )
        create_conversation("foo", "conv1", user, board=board)
        create_conversation("foo2", "conv2", user, board=board)
        create_conversation("foo3", "conv3", user, board=board)

        user_2 = User.objects.create_user("user2@email.br", "password")
        board_2 = Board.objects.create(
            slug="board2", owner=user_2, description="board"
        )
        create_conversation("foo4", "conv4", user_2, board=board_2)
        create_conversation("foo5", "conv5", user_2, board=board_2)

        response = logged_admin.get(url)
        searched_users = response.context["page_object"]
        assert len(searched_users) == 3
        assert searched_users[0].email == user.email
        assert searched_users[0].conversations.count() == 3
        assert searched_users[1].email == user_2.email
        assert searched_users[1].conversations.count() == 2
        assert searched_users[2].email == admin_user.email
        assert searched_users[2].conversations.count() == 0

    def test_get_searched_users_by_comments_count(
        self, logged_admin, admin_user
    ):
        base_url = "/administration/searched-users/"
        url = (
            base_url
            + "?page=1&numEntries=6&orderBy=comments-count&sort=desc&searchString="
        )

        user = User.objects.create_user("user1@email.br", "password")
        board = Board.objects.create(
            slug="board1", owner=user, description="board"
        )
        conversation_1 = create_conversation("foo", "conv1", user, board=board)
        conversation_1.create_comment(
            user, "ad", status="approved", check_limits=False
        )
        conversation_1.create_comment(
            user, "ad2", status="approved", check_limits=False
        )

        response = logged_admin.get(url)
        searched_users = response.context["page_object"]
        assert len(searched_users) == 2
        assert searched_users[0].email == user.email
        assert searched_users[0].comments.count() == 2
        assert searched_users[1].email == admin_user.email
        assert searched_users[1].comments.count() == 0

    def test_get_searched_boards(self, logged_admin, admin_user):
        base_url = "/administration/searched-boards/"
        # search by date
        url = (
            base_url
            + "?page=1&numEntries=6&orderBy=date&sort=desc&searchString="
        )

        user = User.objects.create_user("user1@email.br", "password")
        user_2 = User.objects.create_user("user2@email.br", "password")
        board = Board.objects.create(
            slug="board1", owner=user, description="board"
        )
        board_2 = Board.objects.create(
            slug="board2", owner=user, description="board2"
        )
        Board.objects.create(slug="board3", owner=user_2, description="board3")

        conversation_1 = create_conversation("foo", "conv1", user, board=board)
        conversation_1.create_comment(
            user, "ad", status="approved", check_limits=False
        )
        conversation_1.create_comment(
            user, "ad2", status="approved", check_limits=False
        )

        conversation_2 = create_conversation(
            "foo2", "conv2", user_2, board=board_2
        )
        conversation_2.create_comment(
            user_2, "ad3", status="approved", check_limits=False
        )

        create_conversation("foo3", "conv3", user_2, board=board_2)

        response = logged_admin.get(url)
        searched_boards = response.context["page_object"]

        assert len(searched_boards) == 4
        assert searched_boards[0].slug == "board3"
        assert searched_boards[1].slug == "board2"
        assert searched_boards[2].slug == "board1"
        assert searched_boards[3].slug == admin_user.boards.first().slug

        # search by total conversation
        url = (
            base_url
            + "?page=1&numEntries=6&orderBy=conversations-count&sort=desc&searchString="
        )
        response = logged_admin.get(url)
        searched_boards = response.context["page_object"]

        assert len(searched_boards) == 4
        assert searched_boards[0].slug == "board2"
        assert searched_boards[0].conversations.count() == 2
        assert searched_boards[1].slug == "board1"
        assert searched_boards[1].conversations.count() == 1
        assert searched_boards[2].slug == admin_user.boards.first().slug
        assert searched_boards[2].conversations.count() == 0
        assert searched_boards[3].slug == "board3"
        assert searched_boards[3].conversations.count() == 0

        # search by total comments
        url = (
            base_url
            + "?page=1&numEntries=6&orderBy=comments-count&sort=desc&searchString="
        )
        response = logged_admin.get(url)
        searched_boards = response.context["page_object"]

        assert len(searched_boards) == 4
        assert searched_boards[0].slug == "board1"
        assert searched_boards[0].conversation_set.comments().count() == 2
        assert searched_boards[1].slug == "board2"
        assert searched_boards[1].conversation_set.comments().count() == 1
        assert searched_boards[2].slug == "admintestcom"
        assert searched_boards[2].conversation_set.comments().count() == 0
        assert searched_boards[3].slug == "board3"
        assert searched_boards[3].conversation_set.comments().count() == 0

    def test_get_searched_conversations(self, logged_admin, admin_user):
        base_url = "/administration/searched-conversations/"

        user = User.objects.create_user("user1@email.br", "password")
        board = Board.objects.create(
            slug="board1", owner=user, description="board"
        )
        conversation_1 = create_conversation("foo", "conv1", user, board=board)
        conversation_1.create_comment(
            user, "ad", status="approved", check_limits=False
        )
        conversation_1.create_comment(
            user, "ad2", status="approved", check_limits=False
        )

        conversation_2 = create_conversation("foo2", "conv2", user, board=board)
        conversation_2.create_comment(
            user, "ad3", status="approved", check_limits=False
        )

        board_2 = Board.objects.create(
            slug="board2", owner=admin_user, description="board"
        )
        create_conversation("foo3", "conv3", user, board=board_2)

        # search by date
        url = (
            base_url
            + "?page=1&numEntries=6&orderBy=date&sort=desc&searchString="
        )
        response = logged_admin.get(url)
        searched_conversations = response.context["page_object"]
        assert len(searched_conversations) == 3
        assert searched_conversations[0].title == "conv3"
        assert searched_conversations[1].title == "conv2"
        assert searched_conversations[2].title == "conv1"

        # search by total comments
        url = (
            base_url
            + "?page=1&numEntries=6&orderBy=comments-count&sort=desc&searchString="
        )
        response = logged_admin.get(url)
        searched_conversations = response.context["page_object"]
        assert len(searched_conversations) == 3
        assert searched_conversations[0].title == "conv1"
        assert searched_conversations[0].comments.count() == 2
        assert searched_conversations[1].title == "conv2"
        assert searched_conversations[1].comments.count() == 1
        assert searched_conversations[2].title == "conv3"
        assert searched_conversations[2].comments.count() == 0

    def test_get_users_by_search_string(self, logged_admin, admin_user):
        base_url = "/administration/searched-users/"

        user = User.objects.create_user("user1@email.br", "password")
        user_2 = User.objects.create_user("user2@email.br", "password")

        url = (
            base_url
            + "?page=1&numEntries=6&orderBy=date&sort=desc&searchString=user"
        )

        response = logged_admin.get(url)
        searched_users = response.context["page_object"]
        assert len(searched_users) == 2
        assert searched_users[0].email == user_2.email
        assert searched_users[1].email == user.email

        url = (
            base_url
            + "?page=1&numEntries=6&orderBy=date&sort=desc&searchString=user1"
        )

        response = logged_admin.get(url)
        searched_users = response.context["page_object"]

        assert len(searched_users) == 1
        assert searched_users[0].email == user.email

    def test_get_boards_by_search_string(self, logged_admin, admin_user):
        base_url = "/administration/searched-boards/"

        user = User.objects.create_user("user1@email.br", "password")
        Board.objects.create(slug="test1", owner=user, description="board")
        Board.objects.create(slug="test2", owner=user, description="board2")

        url = (
            base_url
            + "?page=1&numEntries=6&orderBy=date&sort=desc&searchString=test"
        )
        response = logged_admin.get(url)
        searched_boards = response.context["page_object"]
        assert len(searched_boards) == 3
        assert searched_boards[0].slug == "test2"
        assert searched_boards[1].slug == "test1"
        assert searched_boards[2].slug == "admintestcom"

        url = (
            base_url
            + "?page=1&numEntries=6&orderBy=date&sort=desc&searchString=test1"
        )
        response = logged_admin.get(url)
        searched_boards = response.context["page_object"]
        assert len(searched_boards) == 1
        assert searched_boards[0].slug == "test1"

    def test_get_conversations_by_search_string(self, logged_admin, admin_user):
        base_url = "/administration/searched-conversations/"

        user = User.objects.create_user("user1@email.br", "password")
        board = Board.objects.create(
            slug="board1", owner=user, description="board"
        )
        create_conversation("foo", "conv1", user, board=board)
        create_conversation("foo1", "conv2", user, board=board)

        url = (
            base_url
            + "?page=1&numEntries=6&orderBy=date&sort=desc&searchString=conv"
        )
        response = logged_admin.get(url)
        searched_conversations = response.context["page_object"]
        assert len(searched_conversations) == 2

        url = (
            base_url
            + "?page=1&numEntries=6&orderBy=date&sort=desc&searchString=conv1"
        )
        response = logged_admin.get(url)
        searched_conversations = response.context["page_object"]
        assert len(searched_conversations) == 1
