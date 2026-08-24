import mock
import pytest

from ej_boards.models import Board, BoardManagerInvitation
from ej_boards.tasks import send_board_manager_invitation_email
from ej_users.models import User


@pytest.fixture
def board(db):
    owner = User.objects.create_user("owner@example.com", "password")
    return Board.objects.create(owner=owner, title="Board", slug="task-board")


@pytest.fixture
def manager_invitation(board, mk_board_manager_invitation):
    manager = board.owner.__class__.objects.create_user(
        "manager@example.com", "password", name="Manager"
    )
    return mk_board_manager_invitation(
        board,
        manager=manager,
        invited_by=board.owner,
    )


def test_send_board_manager_invitation_email(db, manager_invitation):
    origin = "https://example.com"

    with mock.patch.object(
        BoardManagerInvitation,
        "send_invitation",
    ) as send_invitation:
        send_board_manager_invitation_email(manager_invitation.id, origin)

    send_invitation.assert_called_once_with(origin)


def test_send_board_manager_invitation_email_task_name():
    assert (
        send_board_manager_invitation_email.name
        == "ej_boards.tasks.send_board_manager_invitation_email"
    )


def test_send_board_manager_invitation_email_ignores_missing_invitation(db):
    send_board_manager_invitation_email(999999, "https://example.com")
