import uuid

import mock
import pytest
from django.core import mail
from ej_boards.models import Board
from ej_boards.models import BoardManager, BoardManagerInvitation
from ej_conversations import create_conversation
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from ej_conversations.models import (
    ConversationManager,
    ConversationManagerInvitation,
)
from ej_conversations.models.conversation import Conversation
from ej_conversations.mommy_recipes import ConversationRecipes
from ej_conversations.enums import Choice
from django.urls import reverse
from django.utils.translation import override


class TestBoardModel(ConversationRecipes):
    def test_str_board(self, db, board):
        assert board.title == str(board)

    def test_get_board_absolute_url(self, db, board):
        assert (
            board.get_absolute_url() == f"/boards/{board.slug}/conversations/"
        )

    def test_get_board_palette_from_conversation(
        self, mk_conversation, mk_user
    ):
        user = mk_user(email="someuser@mail.com")
        board = Board.objects.create(
            slug="board1", owner=user, palette="Orange", description="board"
        )
        conversation = create_conversation("foo", "conv1", user, board=board)
        assert conversation.board.palette == "Orange"

    def test_get_board_default_palette_from_conversation(self, mk_user):
        user = mk_user(email="someuser@mail.com")
        board = Board.objects.create(
            slug="board1", owner=user, description="board"
        )
        conversation = create_conversation("foo", "conv1", user, board=board)
        assert conversation.board.palette == "Blue"

    def test_conversation_belongs_to_a_board(self, mk_user):
        user = mk_user(email="someuser@mail.com")
        board = Board.objects.create(
            slug="board1", owner=user, description="board"
        )
        conversation1 = create_conversation("foo", "conv1", user, board=board)
        conversation2 = create_conversation("bar", "conv2", user, board=board)

        assert board.conversations.count() == 2
        assert conversation1.board == board
        assert conversation2.board == board

    def test_conversation_should_not_belong_to_more_than_one_board(
        self, mk_user
    ):
        user = mk_user(email="someuser@mail.com")
        board1 = Board.objects.create(
            slug="board1", owner=user, description="board1"
        )
        board2 = Board.objects.create(
            slug="board2", owner=user, description="board2"
        )
        conversation = create_conversation("foo", "conv1", user, board=board1)
        board2.add_conversation(conversation)

        assert conversation.board == board2
        assert conversation in board2.conversations
        assert conversation not in board1.conversations

    def test_conversation_should_raise_integrity_error_if_there_is_no_board(
        self, mk_user
    ):
        user = mk_user(email="someuser@mail.com")
        with pytest.raises(IntegrityError):
            conversation = Conversation(text="foo", title="conv1", author=user)
            conversation.save()

    def test_tags_should_return_all_the_conversation_tags_of_a_board(
        self, mk_user
    ):
        user = mk_user(email="someuser@mail.com")
        board = Board.objects.create(
            slug="board1", owner=user, description="board1"
        )
        create_conversation("foo", "conv1", user, tags="tag1", board=board)
        create_conversation("bar", "conv2", user, tags="tag2", board=board)

        assert "tag1" == board.tags[0].name
        assert "tag2" == board.tags[1].name

    def test_board_statistics(self, mk_user):
        user = mk_user(email="someuser@mail.com")
        user2 = mk_user(email="someuser2@mail.com")
        board = Board.objects.create(
            slug="board", owner=user, description="board"
        )
        conversation1 = create_conversation("foo", "conv1", user, board=board)
        conversation2 = create_conversation("bar", "conv2", user, board=board)

        comment = conversation1.create_comment(
            user, "ad", status="approved", check_limits=False
        )
        comment2 = conversation2.create_comment(
            user, "ad2", status="approved", check_limits=False
        )

        comment.vote(user, Choice.AGREE)
        comment.vote(user2, Choice.AGREE)
        comment2.vote(user2, Choice.AGREE)

        statistics = board.statistics()

        assert statistics["conversations"] == 2
        assert statistics["votes"] == 3
        assert statistics["participants"] == 3


class TestBoardManagerInvitation(ConversationRecipes):
    def accept_invitation(self, invitation, user=None):
        return invitation.accept(user)

    def test_normalizes_email_before_save(self, db, mk_user):
        owner = mk_user(email="owner@example.com")
        board = Board.objects.create(owner=owner, title="Board", slug="board")

        invitation = BoardManagerInvitation.objects.create(
            board=board,
            email=" Manager@Example.COM ",
            invited_by=owner,
        )

        assert invitation.email == "manager@example.com"

    def test_matches_user_email(self, db, mk_user):
        owner = mk_user(email="owner@example.com")
        manager = mk_user(email=" Manager@Example.COM ")
        board = Board.objects.create(owner=owner, title="Board", slug="board")
        invitation = BoardManagerInvitation.objects.create(
            board=board,
            email="manager@example.com",
            invited_by=owner,
        )

        assert invitation.matches_user_email(manager)

    def test_matches_user_email_rejects_different_email(self, db, mk_user):
        owner = mk_user(email="owner@example.com")
        manager = mk_user(email="other@example.com")
        board = Board.objects.create(owner=owner, title="Board", slug="board")
        invitation = BoardManagerInvitation.objects.create(
            board=board,
            email="manager@example.com",
            invited_by=owner,
        )

        assert not invitation.matches_user_email(manager)

    def test_generates_accept_token(self, db, mk_user):
        owner = mk_user(email="owner@example.com")
        board = Board.objects.create(owner=owner, title="Board", slug="board")

        invitation = BoardManagerInvitation.objects.create(
            board=board,
            email="manager@example.com",
            invited_by=owner,
        )
        other_invitation = BoardManagerInvitation.objects.create(
            board=board,
            email="other-manager@example.com",
            invited_by=owner,
        )

        assert isinstance(invitation.accept_token, uuid.UUID)
        assert invitation.accept_token != other_invitation.accept_token

    def test_prevents_duplicate_active_invitation_for_same_email(
        self, db, mk_user
    ):
        owner = mk_user(email="owner@example.com")
        board = Board.objects.create(owner=owner, title="Board", slug="board")
        BoardManagerInvitation.objects.create(
            board=board,
            email="manager@example.com",
            invited_by=owner,
        )

        with pytest.raises(IntegrityError):
            BoardManagerInvitation.objects.create(
                board=board,
                email="MANAGER@example.com",
                invited_by=owner,
            )

    def test_allows_inactive_duplicate_invitation(self, db, mk_user):
        owner = mk_user(email="owner@example.com")
        board = Board.objects.create(owner=owner, title="Board", slug="board")
        BoardManagerInvitation.objects.create(
            board=board,
            email="manager@example.com",
            invited_by=owner,
        )

        invitation = BoardManagerInvitation.objects.create(
            board=board,
            email="manager@example.com",
            invited_by=owner,
            is_active=False,
        )

        assert invitation.id is not None

    def test_get_board_url(self, db, mk_user):
        owner = mk_user(email="owner@example.com")
        board = Board.objects.create(owner=owner, title="Board", slug="board")
        invitation = BoardManagerInvitation.objects.create(
            board=board,
            email="manager@example.com",
            invited_by=owner,
        )

        assert invitation.get_board_url() == board.get_absolute_url()

    def test_get_accept_url(self, db, mk_user):
        owner = mk_user(email="owner@example.com")
        board = Board.objects.create(owner=owner, title="Board", slug="board")
        invitation = BoardManagerInvitation.objects.create(
            board=board,
            email="manager@example.com",
            invited_by=owner,
        )

        assert invitation.get_accept_url("https://example.com/") == (
            "https://example.com"
            + reverse(
                "boards:board-accept_manager_invitation",
                kwargs={
                    "board_slug": board.slug,
                    "accept_token": invitation.accept_token,
                },
            )
        )

    def test_send_invitation_email(
        self, mk_board, mk_user, mk_board_manager_invitation
    ):
        owner = mk_user(email="owner@example.com", name="Owner")
        board = mk_board(owner=owner)
        manager = mk_user(email="manager@example.com")
        inviter = mk_user(email="inviter@example.com", name="Inviter")
        invitation = mk_board_manager_invitation(
            board,
            manager=manager,
            invited_by=inviter,
        )
        origin = "https://example.com"
        accept_url = invitation.get_accept_url(origin)
        invitation.send_error = "previous failure"
        invitation.save(update_fields=["send_error"])

        with override("en"):
            invitation.send_invitation(origin)

        invitation.refresh_from_db()
        assert len(mail.outbox) == 1
        message = mail.outbox[0]
        assert message.to == [invitation.email]
        assert message.subject.endswith("shared access to an EJ board")
        assert message.content_subtype == "html"
        assert "example.com" in message.body
        assert (
            f"{owner.username} invited you to collaborate on the board "
            f"<strong>{board.title}</strong> on the Empurrando Juntos platform."
        ) in message.body
        assert (
            "By accepting this invitation, you will have access to the board "
            "and will be able to manage its conversations, according to the "
            "permissions granted."
        ) in message.body
        assert "To accept the invitation, click the link below:" in message.body
        assert f'<a href="{accept_url}">{accept_url}</a>' in message.body
        assert "<hr />" in message.body
        assert (
            "Run opinion polls with Empurrando Juntos and understand how your "
            "audience positions itself on a wide range of topics."
        ) in message.body
        assert invitation.sent_at is not None
        assert invitation.send_error == ""

    def test_send_invitation_records_error(
        self, mk_board, mk_board_manager_invitation
    ):
        board = mk_board()
        invitation = mk_board_manager_invitation(board)

        with mock.patch(
            "ej.manager_invitation.EmailMessage.send",
            side_effect=Exception("smtp failed"),
        ):
            invitation.send_invitation("https://example.com")

        invitation.refresh_from_db()
        assert invitation.sent_at is None
        assert invitation.send_error == "smtp failed"

    def test_send_invitation_skips_inactive_invitation(
        self, mk_board, mk_board_manager_invitation
    ):
        board = mk_board()
        invitation = mk_board_manager_invitation(board, is_active=False)
        invitation.send_error = "previous failure"
        invitation.save(update_fields=["send_error"])

        with mock.patch(
            "ej.manager_invitation.EmailMessage.send"
        ) as email_send:
            invitation.send_invitation("https://example.com")

        invitation.refresh_from_db()
        email_send.assert_not_called()
        assert invitation.sent_at is None
        assert invitation.send_error == "previous failure"

    def test_send_invitation_skips_accepted_invitation(
        self, mk_board, mk_user, mk_board_manager_invitation
    ):
        board = mk_board()
        manager = mk_user(email="manager@example.com")
        invitation = mk_board_manager_invitation(
            board,
            manager=manager,
            accepted=True,
        )

        with mock.patch(
            "ej.manager_invitation.EmailMessage.send"
        ) as email_send:
            invitation.send_invitation("https://example.com")

        email_send.assert_not_called()

    def test_accepted_invitation_grants_board_manager_access(self, db, mk_user):
        owner = mk_user(email="owner@example.com")
        manager = mk_user(email="manager@example.com")
        board = Board.objects.create(owner=owner, title="Board", slug="board")
        invitation = BoardManagerInvitation.objects.create(
            board=board,
            email=manager.email,
            invited_by=owner,
        )
        self.accept_invitation(invitation, manager)

        assert BoardManager.objects.filter(board=board, user=manager).exists()
        assert manager.has_perm("ej.is_board_manager", board)
        assert manager.has_perm("ej.can_edit_board", board)

    def test_accepted_invitation_cannot_be_accepted_twice(self, db, mk_user):
        owner = mk_user(email="owner@example.com")
        manager = mk_user(email="manager@example.com")
        board = Board.objects.create(owner=owner, title="Board", slug="board")
        invitation = BoardManagerInvitation.objects.create(
            board=board,
            email=manager.email,
            invited_by=owner,
        )
        self.accept_invitation(invitation, manager)

        with pytest.raises(ValidationError):
            invitation.accept(manager)

        assert (
            BoardManager.objects.filter(board=board, user=manager).count() == 1
        )

    def test_accepted_invitation_grants_access_after_user_registers(
        self, db, mk_user
    ):
        owner = mk_user(email="owner@example.com")
        board = Board.objects.create(owner=owner, title="Board", slug="board")
        invitation = BoardManagerInvitation.objects.create(
            board=board,
            email="manager@example.com",
            invited_by=owner,
        )
        manager = mk_user(email="manager@example.com")
        invitation.refresh_from_db()
        self.accept_invitation(invitation)

        assert manager.has_perm("ej.is_board_manager", board)
        assert manager.has_perm("ej.can_edit_board", board)

    def test_pending_invitation_does_not_create_manager_or_grant_access(
        self, db, mk_user
    ):
        owner = mk_user(email="owner@example.com")
        manager = mk_user(email="manager@example.com")
        board = Board.objects.create(owner=owner, title="Board", slug="board")
        BoardManagerInvitation.objects.create(
            board=board,
            email=manager.email,
            invited_by=owner,
        )

        assert not BoardManager.objects.filter(
            board=board, user=manager
        ).exists()
        assert not manager.has_perm("ej.is_board_manager", board)
        assert not manager.has_perm("ej.can_edit_board", board)

    def test_inactive_invitation_cannot_be_accepted(self, db, mk_user):
        owner = mk_user(email="owner@example.com")
        manager = mk_user(email="manager@example.com")
        board = Board.objects.create(owner=owner, title="Board", slug="board")
        invitation = BoardManagerInvitation.objects.create(
            board=board,
            email=manager.email,
            invited_by=owner,
            is_active=False,
        )

        with pytest.raises(ValidationError):
            invitation.accept(manager)

        invitation.refresh_from_db()
        assert not invitation.is_active
        assert invitation.status == BoardManagerInvitation.Status.PENDING
        assert not BoardManager.objects.filter(
            board=board, user=manager
        ).exists()

    def test_resaving_accepted_invitation_does_not_duplicate_managers(
        self, db, mk_user
    ):
        owner = mk_user(email="owner@example.com")
        manager = mk_user(email="manager@example.com")
        board = Board.objects.create(owner=owner, title="Board", slug="board")
        invitation = BoardManagerInvitation.objects.create(
            board=board,
            email=manager.email,
            invited_by=owner,
        )

        self.accept_invitation(invitation, manager)
        invitation.save()

        assert (
            BoardManager.objects.filter(board=board, user=manager).count() == 1
        )

    def test_accepting_new_invitation_invalidates_previous_manager_invitation(
        self, db, mk_user
    ):
        owner = mk_user(email="owner@example.com")
        manager = mk_user(email="manager@example.com")
        board = Board.objects.create(owner=owner, title="Board", slug="board")
        previous_invitation = BoardManagerInvitation.objects.create(
            board=board,
            email=manager.email,
            invited_by=owner,
        )
        self.accept_invitation(previous_invitation, manager)
        new_invitation = BoardManagerInvitation.objects.create(
            board=board,
            email="manager-alias@example.com",
            user=manager,
            invited_by=owner,
        )

        self.accept_invitation(new_invitation, manager)
        previous_invitation.refresh_from_db()

        manager_membership = BoardManager.objects.get(board=board, user=manager)
        assert manager_membership.invitation == new_invitation
        assert not previous_invitation.is_active
        assert new_invitation.is_active

    def test_delete_manager_removes_manager_access(self, db, mk_user):
        owner = mk_user(email="owner@example.com")
        manager = mk_user(email="manager@example.com")
        board = Board.objects.create(owner=owner, title="Board", slug="board")
        invitation = BoardManagerInvitation.objects.create(
            board=board,
            email=manager.email,
            invited_by=owner,
        )
        self.accept_invitation(invitation, manager)

        invitation.delete_manager()
        invitation.refresh_from_db()

        assert not invitation.is_active
        assert not BoardManager.objects.filter(
            board=board, user=manager
        ).exists()
        assert not manager.has_perm("ej.is_board_manager", board)
        assert not manager.has_perm("ej.can_edit_board", board)

        replacement = BoardManagerInvitation.objects.create(
            board=board,
            email=manager.email,
            invited_by=owner,
        )
        self.accept_invitation(replacement, manager)

        assert (
            BoardManager.objects.get(board=board, user=manager).invitation
            == replacement
        )

    def test_deactivating_accepted_invitation_removes_manager_access(
        self, db, mk_user
    ):
        owner = mk_user(email="owner@example.com")
        manager = mk_user(email="manager@example.com")
        board = Board.objects.create(owner=owner, title="Board", slug="board")
        invitation = BoardManagerInvitation.objects.create(
            board=board,
            email=manager.email,
            invited_by=owner,
        )
        self.accept_invitation(invitation, manager)

        invitation.is_active = False
        invitation.save(update_fields=["is_active"])

        assert not BoardManager.objects.filter(
            board=board, user=manager
        ).exists()
        assert not manager.has_perm("ej.is_board_manager", board)

    def test_deleting_invitation_removes_manager_access(self, db, mk_user):
        owner = mk_user(email="owner@example.com")
        manager = mk_user(email="manager@example.com")
        board = Board.objects.create(owner=owner, title="Board", slug="board")
        invitation = BoardManagerInvitation.objects.create(
            board=board,
            email=manager.email,
            invited_by=owner,
        )
        self.accept_invitation(invitation, manager)

        invitation.delete()

        assert not BoardManager.objects.filter(
            board=board, user=manager
        ).exists()

    def test_board_and_conversation_manager_roles_are_independent(
        self, db, mk_user
    ):
        owner = mk_user(email="owner@example.com")
        manager = mk_user(email="manager@example.com")
        board = Board.objects.create(owner=owner, title="Board", slug="board")
        conversation = create_conversation(
            "Question?",
            "Question?",
            owner,
            board=board,
        )
        board_invitation = BoardManagerInvitation.objects.create(
            board=board,
            email=manager.email,
            invited_by=owner,
        )
        conversation_invitation = ConversationManagerInvitation.objects.create(
            conversation=conversation,
            email=manager.email,
            invited_by=owner,
        )
        board_invitation.accept(manager)
        conversation_invitation.accept(manager)

        conversation_invitation.delete_manager()
        conversation_invitation.refresh_from_db()
        assert not conversation_invitation.is_active
        assert manager.has_perm("ej.can_edit_conversation", conversation)
        assert not ConversationManager.objects.filter(
            conversation=conversation,
            user=manager,
        ).exists()

        board_invitation.delete_manager()
        board_invitation.refresh_from_db()
        assert not board_invitation.is_active
        assert not manager.has_perm("ej.can_edit_conversation", conversation)

        replacement_conversation_invitation = (
            ConversationManagerInvitation.objects.create(
                conversation=conversation,
                email=manager.email,
                invited_by=owner,
            )
        )
        replacement_conversation_invitation.accept(manager)
        assert manager.has_perm("ej.can_edit_conversation", conversation)
