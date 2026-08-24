from django.test import Client
from django.db import IntegrityError
from django.utils.translation import gettext as _
import mock
import pytest
from urllib.parse import parse_qs, urlparse

from ej_conversations.mommy_recipes import ConversationRecipes
from ej_users.models import User
from ej_boards.models import Board, BoardManager, BoardManagerInvitation
from ej_conversations import create_conversation
from ej_conversations.models import Conversation
from ej_conversations.views import BoardConversationsView
from django.shortcuts import reverse
from ej_boards.views import BoardListView


class TestBoardsView(ConversationRecipes):
    def assert_member_toast(self, content, message):
        assert 'class="toast' in content
        assert str(message) in content

    def accept_invitation_url(self, board, invitation):
        return reverse(
            "boards:board-accept_manager_invitation",
            kwargs={
                "board_slug": board.slug,
                "accept_token": invitation.accept_token,
            },
        )

    def assert_redirects_with_next(self, response, auth_route, next_url):
        assert response.status_code == 302
        parsed_url = urlparse(response.url)
        assert parsed_url.path == reverse(auth_route)
        assert parse_qs(parsed_url.query)["next"] == [next_url]

    def test_managed_boards_appear_in_lists_and_switchers(self, db, rf):
        owner = User.objects.create_user("owner@email.br", "password")
        manager = User.objects.create_user("manager@email.br", "password")
        board = Board.objects.create(
            slug="board", owner=owner, description="board"
        )
        BoardManager.objects.create(board=board, user=manager)
        request = rf.get("/")
        request.user = manager

        board_list = BoardListView()
        board_list.setup(request)
        assert board in board_list.get_context_data()["boards"]

        conversations = BoardConversationsView()
        conversations.setup(request, board_slug=board.slug)
        context = conversations.get_context_data()
        assert board in context["user_boards"]
        assert not context["can_delete_board"]

    def test_create_view_renders_breadcrumb_without_side_menu(self, db):
        user = User.objects.create_user("user@email.br", "password")
        client = Client()
        client.force_login(user)

        response = client.get(reverse("boards:board-create"))

        assert response.status_code == 200
        assert b'class="breadcrumb"' in response.content
        assert response.content.count(b'<li class="breadcrumb__item') == 2
        assert (
            f'aria-current="page">{_("Create board")}'.encode()
            in response.content
        )
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
        assert f">{_("Board")}<".encode() in response.content
        assert (
            f'aria-current="page">{_("Settings")}'.encode() in response.content
        )
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

    def test_manager_can_edit_board_but_cannot_delete_or_add_conversations(
        self, db
    ):
        owner = User.objects.create_user("owner@email.br", "password")
        manager = User.objects.create_user("manager@email.br", "password")
        board = Board.objects.create(
            slug="board", owner=owner, description="board"
        )
        BoardManager.objects.create(board=board, user=manager)
        client = Client()
        client.force_login(manager)

        edit_url = reverse(
            "boards:board-edit", kwargs={"board_slug": board.slug}
        )
        delete_url = reverse(
            "boards:board-delete", kwargs={"board_slug": board.slug}
        )
        create_url = reverse(
            "boards:conversation-create",
            kwargs={"board_slug": board.slug},
        )

        response = client.get(edit_url)
        assert response.status_code == 200

        response = client.get(board.get_absolute_url())
        create_button = (
            f'<a class="is-primary button square" href="{create_url}">'.encode()
        )
        assert create_button not in response.content

        response = client.post(delete_url)
        assert response.status_code == 302
        assert response.url == "/login/"
        assert Board.objects.filter(id=board.id).exists()

        response = client.get(create_url)
        assert response.status_code == 302
        assert response.url == "/login/"

    def test_create_board_manager_invitation(self, db):
        owner = User.objects.create_user("owner@email.br", "password")
        manager = User.objects.create_user("manager@email.br", "password")
        board = Board.objects.create(
            slug="board", owner=owner, description="board"
        )
        url = reverse(
            "boards:board-create_manager_invitation",
            kwargs={"board_slug": board.slug},
        )
        client = Client()
        client.force_login(owner)

        with mock.patch(
            "ej_boards.views.send_board_manager_invitation_email.delay"
        ) as delay:
            response = client.post(url, {"email": " Manager@Email.BR "})

        invitation = BoardManagerInvitation.objects.get(
            board=board,
            email="manager@email.br",
        )
        assert response.status_code == 201
        assert response.content == b""
        assert invitation.user == manager
        assert invitation.invited_by == owner
        assert invitation.status == BoardManagerInvitation.Status.PENDING
        assert not BoardManager.objects.filter(
            board=board, user=manager
        ).exists()
        delay.assert_called_once_with(invitation.id, "http://localhost:8000")

    def test_create_board_manager_invitation_without_existing_user(self, db):
        owner = User.objects.create_user("owner@email.br", "password")
        board = Board.objects.create(
            slug="board", owner=owner, description="board"
        )
        url = reverse(
            "boards:board-create_manager_invitation",
            kwargs={"board_slug": board.slug},
        )
        client = Client()
        client.force_login(owner)

        response = client.post(url, {"email": "new-manager@email.br"})

        invitation = BoardManagerInvitation.objects.get(
            board=board,
            email="new-manager@email.br",
        )
        assert response.status_code == 201
        assert invitation.user is None
        assert invitation.invited_by == owner

    def test_create_board_manager_invitation_ignores_enqueue_error(self, db):
        owner = User.objects.create_user("owner@email.br", "password")
        board = Board.objects.create(
            slug="board", owner=owner, description="board"
        )
        url = reverse(
            "boards:board-create_manager_invitation",
            kwargs={"board_slug": board.slug},
        )
        client = Client()
        client.force_login(owner)

        with mock.patch(
            "ej_boards.views.send_board_manager_invitation_email.delay",
            side_effect=Exception("broker unavailable"),
        ):
            response = client.post(url, {"email": "manager@email.br"})

        assert response.status_code == 201
        assert BoardManagerInvitation.objects.filter(
            board=board,
            email="manager@email.br",
        ).exists()

    def test_create_board_manager_invitation_rejects_owner_email(self, db):
        owner = User.objects.create_user("owner@email.br", "password")
        board = Board.objects.create(
            slug="board", owner=owner, description="board"
        )
        url = reverse(
            "boards:board-create_manager_invitation",
            kwargs={"board_slug": board.slug},
        )
        client = Client()
        client.force_login(owner)

        response = client.post(url, {"email": owner.email})

        assert response.status_code == 400
        assert str(_("The board owner cannot be added as a manager.")) in (
            response.content.decode()
        )
        assert not BoardManagerInvitation.objects.filter(
            board=board,
            email=owner.email,
        ).exists()

    def test_create_board_manager_invitation_rejects_invalid_email(self, db):
        owner = User.objects.create_user("owner@email.br", "password")
        board = Board.objects.create(
            slug="board", owner=owner, description="board"
        )
        url = reverse(
            "boards:board-create_manager_invitation",
            kwargs={"board_slug": board.slug},
        )
        client = Client()
        client.force_login(owner)

        response = client.post(url, {"email": "invalid-email"})

        assert response.status_code == 400
        assert (
            str(_("Enter a valid email address.")) in response.content.decode()
        )
        assert not BoardManagerInvitation.objects.filter(board=board).exists()

    def test_create_board_manager_invitation_rejects_duplicate_active(
        self, db, mk_board_manager_invitation
    ):
        owner = User.objects.create_user("owner@email.br", "password")
        board = Board.objects.create(
            slug="board", owner=owner, description="board"
        )
        mk_board_manager_invitation(
            board,
            email="manager@email.br",
            invited_by=owner,
        )
        url = reverse(
            "boards:board-create_manager_invitation",
            kwargs={"board_slug": board.slug},
        )
        client = Client()
        client.force_login(owner)

        response = client.post(url, {"email": "manager@email.br"})

        assert response.status_code == 400
        assert (
            str(_("This member is already invited."))
            in response.content.decode()
        )
        assert (
            BoardManagerInvitation.objects.filter(
                board=board,
                email="manager@email.br",
            ).count()
            == 1
        )

    def test_create_board_manager_invitation_handles_duplicate_race(self, db):
        owner = User.objects.create_user("owner@email.br", "password")
        board = Board.objects.create(
            slug="board", owner=owner, description="board"
        )
        url = reverse(
            "boards:board-create_manager_invitation",
            kwargs={"board_slug": board.slug},
        )
        client = Client()
        client.force_login(owner)

        with mock.patch(
            "ej_boards.views.BoardManagerInvitation.objects.create",
            side_effect=IntegrityError,
        ):
            response = client.post(url, {"email": "manager@email.br"})

        assert response.status_code == 400
        assert (
            str(_("This member is already invited."))
            in response.content.decode()
        )

    def test_create_board_manager_invitation_rejects_existing_manager(self, db):
        owner = User.objects.create_user("owner@email.br", "password")
        manager = User.objects.create_user("manager@email.br", "password")
        board = Board.objects.create(
            slug="board", owner=owner, description="board"
        )
        BoardManager.objects.create(board=board, user=manager)
        url = reverse(
            "boards:board-create_manager_invitation",
            kwargs={"board_slug": board.slug},
        )
        client = Client()
        client.force_login(owner)

        response = client.post(url, {"email": manager.email})

        assert response.status_code == 400
        assert (
            str(_("This member is already invited."))
            in response.content.decode()
        )
        assert not BoardManagerInvitation.objects.filter(board=board).exists()

    def test_delete_board_manager_invitation_removes_member(
        self, db, mk_board_manager_invitation
    ):
        owner = User.objects.create_user("owner@email.br", "password")
        manager = User.objects.create_user("manager@email.br", "password")
        board = Board.objects.create(
            slug="board", owner=owner, description="board"
        )
        invitation = mk_board_manager_invitation(
            board,
            manager=manager,
            invited_by=owner,
            accepted=True,
        )
        url = reverse(
            "boards:board-delete_manager_invitation",
            kwargs={"board_slug": board.slug, "invitation_id": invitation.id},
        )
        client = Client()
        client.force_login(owner)

        response = client.delete(url)
        invitation.refresh_from_db()

        assert response.status_code == 204
        assert response.content == b""
        assert not invitation.is_active
        assert not BoardManager.objects.filter(
            board=board, user=manager
        ).exists()
        assert not manager.has_perm("ej.can_edit_board", board)

    def test_non_owner_cannot_manage_board_invitations(self, db):
        owner = User.objects.create_user("owner@email.br", "password")
        manager = User.objects.create_user("manager@email.br", "password")
        board = Board.objects.create(
            slug="board", owner=owner, description="board"
        )
        BoardManager.objects.create(board=board, user=manager)
        create_url = reverse(
            "boards:board-create_manager_invitation",
            kwargs={"board_slug": board.slug},
        )
        delete_url = reverse(
            "boards:board-delete_manager_invitation",
            kwargs={"board_slug": board.slug, "invitation_id": 999},
        )
        client = Client()
        client.force_login(manager)

        response = client.post(create_url, {"email": "other@email.br"})
        assert response.status_code == 302
        assert response.url == "/login/"

        response = client.delete(delete_url)
        assert response.status_code == 302
        assert response.url == "/login/"

    @pytest.mark.parametrize(
        "is_staff, is_superuser", [(True, False), (False, True)]
    )
    def test_non_owner_admin_cannot_manage_board_invitations(
        self, db, is_staff, is_superuser
    ):
        owner = User.objects.create_user("owner@email.br", "password")
        admin = User.objects.create_user(
            "admin@email.br",
            "password",
            is_staff=is_staff,
            is_superuser=is_superuser,
        )
        manager = User.objects.create_user("manager@email.br", "password")
        board = Board.objects.create(
            slug="board", owner=owner, description="board"
        )
        invitation = BoardManagerInvitation.objects.create(
            board=board,
            email=manager.email,
            user=manager,
            invited_by=owner,
        )
        create_url = reverse(
            "boards:board-create_manager_invitation",
            kwargs={"board_slug": board.slug},
        )
        delete_url = reverse(
            "boards:board-delete_manager_invitation",
            kwargs={"board_slug": board.slug, "invitation_id": invitation.id},
        )
        client = Client()
        client.force_login(admin)

        response = client.post(create_url, {"email": "other@email.br"})
        assert response.status_code == 302
        assert response.url == "/login/"

        response = client.delete(delete_url)
        assert response.status_code == 302
        assert response.url == "/login/"

    def test_accept_board_manager_invitation(
        self, db, mk_board_manager_invitation
    ):
        owner = User.objects.create_user("owner@email.br", "password")
        manager = User.objects.create_user("manager@email.br", "password")
        board = Board.objects.create(
            slug="board", owner=owner, description="board"
        )
        invitation = mk_board_manager_invitation(
            board,
            manager=manager,
            invited_by=owner,
        )
        url = self.accept_invitation_url(board, invitation)
        client = Client()
        client.force_login(manager)

        response = client.get(url)

        invitation.refresh_from_db()
        assert response.status_code == 302
        assert response.url == board.get_absolute_url()
        assert invitation.status == BoardManagerInvitation.Status.ACCEPTED
        assert invitation.user == manager
        assert BoardManager.objects.filter(board=board, user=manager).exists()

    def test_accept_board_manager_invitation_uses_member_toast(
        self, db, mk_board_manager_invitation
    ):
        owner = User.objects.create_user("owner@email.br", "password")
        manager = User.objects.create_user("manager@email.br", "password")
        board = Board.objects.create(
            slug="board", owner=owner, description="board"
        )
        invitation = mk_board_manager_invitation(
            board,
            manager=manager,
            invited_by=owner,
        )
        url = self.accept_invitation_url(board, invitation)
        client = Client()
        client.force_login(manager)

        response = client.get(url, follow=True)

        assert response.redirect_chain == [(board.get_absolute_url(), 302)]
        self.assert_member_toast(
            response.content.decode(), _("Invitation accepted.")
        )

    def test_accepted_board_manager_invitation_cannot_be_reused(
        self, db, mk_board_manager_invitation
    ):
        owner = User.objects.create_user("owner@email.br", "password")
        manager = User.objects.create_user("manager@email.br", "password")
        board = Board.objects.create(
            slug="board", owner=owner, description="board"
        )
        invitation = mk_board_manager_invitation(
            board,
            manager=manager,
            invited_by=owner,
        )
        url = self.accept_invitation_url(board, invitation)
        client = Client()
        client.force_login(manager)

        assert client.get(url).status_code == 302
        assert client.get(url).status_code == 404

    def test_accept_board_manager_invitation_redirects_existing_user_to_login(
        self, db, mk_board_manager_invitation
    ):
        owner = User.objects.create_user("owner@email.br", "password")
        manager = User.objects.create_user("manager@email.br", "password")
        board = Board.objects.create(
            slug="board", owner=owner, description="board"
        )
        invitation = mk_board_manager_invitation(
            board,
            manager=manager,
            invited_by=owner,
        )
        url = self.accept_invitation_url(board, invitation)

        response = Client().get(url)

        self.assert_redirects_with_next(response, "auth:login", url)

    def test_accept_board_manager_invitation_redirects_new_user_to_register(
        self, db, mk_board_manager_invitation
    ):
        owner = User.objects.create_user("owner@email.br", "password")
        board = Board.objects.create(
            slug="board", owner=owner, description="board"
        )
        invitation = mk_board_manager_invitation(
            board,
            email="new-manager@email.br",
            invited_by=owner,
        )
        url = self.accept_invitation_url(board, invitation)

        response = Client().get(url)

        self.assert_redirects_with_next(response, "auth:register", url)

    def test_accept_board_manager_invitation_rejects_email_mismatch(
        self, db, mk_board_manager_invitation
    ):
        owner = User.objects.create_user("owner@email.br", "password")
        manager = User.objects.create_user("manager@email.br", "password")
        other_user = User.objects.create_user("other@email.br", "password")
        board = Board.objects.create(
            slug="board", owner=owner, description="board"
        )
        invitation = mk_board_manager_invitation(
            board,
            manager=manager,
            invited_by=owner,
        )
        url = self.accept_invitation_url(board, invitation)
        client = Client()
        client.force_login(other_user)

        response = client.get(url)

        invitation.refresh_from_db()
        assert response.status_code == 302
        assert response.url == other_user.profile.default_url()
        toast_response = client.get(response.url, follow=True)
        self.assert_member_toast(
            toast_response.content.decode(),
            _("This invitation was sent to a different email address."),
        )
        assert invitation.status == BoardManagerInvitation.Status.PENDING
        assert invitation.is_active
        assert not BoardManager.objects.filter(
            board=board, user=other_user
        ).exists()

    def test_accept_board_manager_invitation_rejects_inactive_invitation(
        self, db, mk_board_manager_invitation
    ):
        owner = User.objects.create_user("owner@email.br", "password")
        manager = User.objects.create_user("manager@email.br", "password")
        board = Board.objects.create(
            slug="board", owner=owner, description="board"
        )
        invitation = mk_board_manager_invitation(
            board,
            manager=manager,
            invited_by=owner,
            is_active=False,
        )
        url = self.accept_invitation_url(board, invitation)
        client = Client()
        client.force_login(manager)

        response = client.get(url)

        assert response.status_code == 404

    def test_board_manager_reaches_conversation_edit_and_dashboard(self, db):
        owner = User.objects.create_user("owner@email.br", "password")
        manager = User.objects.create_user("manager@email.br", "password")
        board = Board.objects.create(
            slug="board", owner=owner, description="board"
        )
        conversation = create_conversation(
            "Question?",
            "Question?",
            owner,
            board=board,
        )
        BoardManager.objects.create(board=board, user=manager)
        client = Client()
        client.force_login(manager)

        edit_url = reverse(
            "boards:conversation-edit", kwargs=conversation.get_url_kwargs()
        )
        dashboard_url = reverse(
            "boards:dataviz-dashboard", kwargs=conversation.get_url_kwargs()
        )

        assert client.get(edit_url).status_code == 200
        assert client.get(dashboard_url).status_code == 200
