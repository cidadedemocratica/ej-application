from itertools import count

import pytest

from ej_boards.models import BoardManagerInvitation

INVITATION_EMAIL_SEQUENCE = count(1)


@pytest.fixture
def mk_board_manager_invitation(db):
    def make(
        board,
        *,
        manager=None,
        email=None,
        invited_by=None,
        status=None,
        is_active=True,
        accepted=False,
    ):
        if manager is not None:
            email = manager.email
        if email is None:
            sequence = next(INVITATION_EMAIL_SEQUENCE)
            email = f"board-manager-{sequence}@example.com"
        if invited_by is None:
            invited_by = board.owner

        invitation = BoardManagerInvitation.objects.create(
            board=board,
            email=email,
            invited_by=invited_by,
            is_active=is_active,
            **({"status": status} if status is not None else {}),
        )
        if accepted:
            invitation.accept(manager)
        return invitation

    return make
