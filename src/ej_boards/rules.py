from constance import config
from django.conf import settings

from boogie import rules
from .models import Board


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
        user.has_perm("ej.can_edit_board", board)
        and (board.conversations.count() < rules.compute("ej.board_conversation_limit", user))
    )


@rules.register_perm("ej.can_edit_board")
def can_edit_board(user, board):
    """
    Verify if a user can edit some board.
    """
    return user == board.owner


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
