import pytest
from django.test import override_settings

from ej_boards.models import Board, BoardManagerInvitation
from ej_boards.rules import (
    can_add_conversation_to_board,
    can_manage_board_members,
)
from ej_conversations import create_conversation
from ej_conversations.models import Conversation, ConversationManager
from ej_users.models import User


@pytest.fixture
def board_manager(db):
    owner = User.objects.create_user("owner@example.com", "password")
    manager = User.objects.create_user("manager@example.com", "password")
    board = Board.objects.create(
        owner=owner,
        title="Board",
        slug="board",
    )
    invitation = BoardManagerInvitation.objects.create(
        board=board,
        email=manager.email,
        invited_by=owner,
    )
    invitation.accept(manager)
    return board, manager


def test_accepted_board_manager_permissions(board_manager):
    board, manager = board_manager

    assert manager.has_perm("ej.is_board_manager", board)
    assert manager.has_perm("ej.can_access_board", board)
    assert manager.has_perm("ej.can_edit_board", board)
    assert not manager.has_perm("ej.can_add_conversation_to_board", board)
    assert not manager.has_perm("ej.can_delete_board", board)
    assert not manager.has_perm("ej.can_manage_board_members", board)


@pytest.mark.parametrize(
    "is_staff, is_superuser", [(True, False), (False, True)]
)
def test_non_owner_staff_cannot_manage_board_members(
    db, is_staff, is_superuser
):
    owner = User.objects.create_user("owner@example.com", "password")
    user = User.objects.create_user(
        "admin@example.com",
        "password",
        is_staff=is_staff,
        is_superuser=is_superuser,
    )
    board = Board.objects.create(owner=owner, title="Board", slug="board")

    assert not can_manage_board_members(user, board)


@override_settings(EJ_MAX_CONVERSATIONS_PER_BOARD=1)
def test_board_owner_can_add_conversation_below_limit(db):
    owner = User.objects.create_user("owner@example.com", "password")
    board = Board.objects.create(owner=owner, title="Board", slug="board")

    assert can_add_conversation_to_board(owner, board)


@override_settings(EJ_MAX_CONVERSATIONS_PER_BOARD=1)
def test_board_owner_cannot_add_conversation_at_limit(db):
    owner = User.objects.create_user("owner@example.com", "password")
    board = Board.objects.create(owner=owner, title="Board", slug="board")
    create_conversation("Conversation", "Text", owner, board=board)

    assert not can_add_conversation_to_board(owner, board)


def test_board_manager_cannot_add_conversation_below_limit(board_manager):
    board, manager = board_manager

    assert not can_add_conversation_to_board(manager, board)


def test_non_owner_staff_cannot_add_conversation_below_limit(db):
    owner = User.objects.create_user("owner@example.com", "password")
    staff = User.objects.create_user(
        "staff@example.com", "password", is_staff=True
    )
    board = Board.objects.create(owner=owner, title="Board", slug="board")

    assert not can_add_conversation_to_board(staff, board)


@pytest.mark.parametrize("is_active", [True, False])
def test_pending_or_inactive_invitation_grants_no_board_permissions(
    db, is_active
):
    owner = User.objects.create_user("owner@example.com", "password")
    manager = User.objects.create_user("manager@example.com", "password")
    board = Board.objects.create(
        owner=owner,
        title="Board",
        slug="board",
    )
    BoardManagerInvitation.objects.create(
        board=board,
        email=manager.email,
        invited_by=owner,
        is_active=is_active,
    )

    assert not manager.has_perm("ej.is_board_manager", board)
    assert not manager.has_perm("ej.can_access_board", board)
    assert not manager.has_perm("ej.can_edit_board", board)


def test_board_manager_implicitly_manages_existing_and_future_conversations(
    board_manager,
):
    board, manager = board_manager
    existing_conversation = create_conversation(
        "Existing conversation",
        "Existing conversation",
        board.owner,
        board=board,
    )

    assert manager.has_perm("ej.is_conversation_manager", existing_conversation)
    assert manager.has_perm("ej.can_edit_conversation", existing_conversation)
    assert not manager.has_perm(
        "ej.can_delete_conversation", existing_conversation
    )
    assert not manager.has_perm(
        "ej.can_manage_conversation_members", existing_conversation
    )
    assert not ConversationManager.objects.filter(
        conversation=existing_conversation,
        user=manager,
    ).exists()

    future_conversation = create_conversation(
        "Future conversation",
        "Future conversation",
        board.owner,
        board=board,
    )

    assert manager.has_perm("ej.is_conversation_manager", future_conversation)
    assert not ConversationManager.objects.filter(
        conversation=future_conversation,
        user=manager,
    ).exists()


def test_managed_by_includes_board_manager_conversations(board_manager):
    board, manager = board_manager
    conversation = create_conversation(
        "Board conversation",
        "Board conversation",
        board.owner,
        board=board,
    )

    assert list(Conversation.objects.managed_by(manager)) == [conversation]


def test_accessible_by_includes_managed_boards(board_manager):
    board, manager = board_manager

    assert list(Board.objects.accessible_by(manager)) == [board]
