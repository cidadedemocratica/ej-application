from boogie import rules
from .models import Board


@rules.register_rule('ej_boards.has_board')
def has_board(user):
    """
    Verify if an user has a conversation board.
    """
    if Board.objects.filter(owner=user):
        return True
    else:
        return False


@rules.register_perm('ej_boards.can_add_conversation')
def can_add_conversation(user, board):
    if board.owner == user:
        return True

    return False
