from constance import config
from django.conf import settings

from boogie import rules
from .models import Board


def _is_authenticated(user):
    return bool(
        getattr(user, "is_authenticated", False) and user.id is not None
    )


def _is_board_owner_or_admin(user, board):
    return _is_authenticated(user) and (
        user.id == board.owner_id or user.is_staff or user.is_superuser
    )


@rules.register_rule("ej.user_has_board")
def user_has_board(user):
    """
    Verify if an user has a conversation board.
    """
    if Board.objects.filter(owner=user):
        return True
    else:
        return False


@rules.register_perm("ej.can_add_conversation_to_board")
def can_add_conversation_to_board(user, board):
    return bool(
        _is_authenticated(user)
        and user.id == board.owner_id
        and board.conversations.count()
        < rules.compute("ej.board_conversation_limit", user)
    )


@rules.register_value("ej.board_conversation_limit")
def board_conversation_limit(user):
    return settings.EJ_MAX_CONVERSATIONS_PER_BOARD or float("inf")


@rules.register_perm("ej.is_board_manager")
def is_board_manager(user, board):
    return _is_authenticated(user) and board.managers.filter(user=user).exists()


@rules.register_perm("ej.can_edit_board")
def can_edit_board(user, board):
    """
    Verify if a user can edit some board.
    """
    return _is_board_owner_or_admin(user, board) or user.has_perm(
        "ej.is_board_manager", board
    )


@rules.register_perm("ej.can_access_board")
def can_access_board(user, board):
    """
    Verify if a user can access a board's conversation list.
    """
    return _is_board_owner_or_admin(user, board) or user.has_perm(
        "ej.is_board_manager", board
    )


@rules.register_perm("ej.can_delete_board")
def can_delete_board(user, board):
    return _is_board_owner_or_admin(user, board)


@rules.register_perm("ej.can_manage_board_members")
def can_manage_board_members(user, board):
    """
    Verify if a user can manage board members.
    Notice: Only the board owner can manage board members, even staff/superusers can't.
    """
    return _is_authenticated(user) and user.id == board.owner_id


@rules.register_perm("ej.can_add_board")
def can_add_board(user):
    """
    Verify if a user can create a board following the
    django admin permission and the max board number.
    """
    return (
        user.has_perm("ej_boards.add_board")
        or Board.objects.filter(owner=user).count() < config.EJ_MAX_BOARD_NUMBER
    )


@rules.register_perm("ej.can_access_environment_management")
def can_access_admin_board(user):
    return user.is_superuser
