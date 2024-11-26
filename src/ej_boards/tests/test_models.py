from ej_boards.models import Board
from ej_conversations import create_conversation
from django.db import IntegrityError
from ej_conversations.models.conversation import Conversation
from ej_conversations.mommy_recipes import ConversationRecipes
from ej_conversations.enums import Choice
import pytest


class TestBoardModel(ConversationRecipes):
    def test_str_board(self, db, board):
        assert board.title == str(board)

    def test_get_board_absolute_url(self, db, board):
        assert board.get_absolute_url() == f"/boards/{board.slug}/conversations/"

    def test_get_board_palette_from_conversation(self, mk_conversation, mk_user):
        user = mk_user(email="someuser@mail.com")
        board = Board.objects.create(
            slug="board1", owner=user, palette="Orange", description="board"
        )
        conversation = create_conversation("foo", "conv1", user, board=board)
        assert conversation.board.palette == "Orange"

    def test_get_board_default_palette_from_conversation(self, mk_user):
        user = mk_user(email="someuser@mail.com")
        board = Board.objects.create(slug="board1", owner=user, description="board")
        conversation = create_conversation("foo", "conv1", user, board=board)
        assert conversation.board.palette == "Blue"

    def test_conversation_belongs_to_a_board(self, mk_user):
        user = mk_user(email="someuser@mail.com")
        board = Board.objects.create(slug="board1", owner=user, description="board")
        conversation1 = create_conversation("foo", "conv1", user, board=board)
        conversation2 = create_conversation("bar", "conv2", user, board=board)

        assert board.conversations.count() == 2
        assert conversation1.board == board
        assert conversation2.board == board

    def test_conversation_should_not_belong_to_more_than_one_board(self, mk_user):
        user = mk_user(email="someuser@mail.com")
        board1 = Board.objects.create(slug="board1", owner=user, description="board1")
        board2 = Board.objects.create(slug="board2", owner=user, description="board2")
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

    def test_tags_should_return_all_the_conversation_tags_of_a_board(self, mk_user):
        user = mk_user(email="someuser@mail.com")
        board = Board.objects.create(slug="board1", owner=user, description="board1")
        create_conversation("foo", "conv1", user, tags="tag1", board=board)
        create_conversation("bar", "conv2", user, tags="tag2", board=board)

        assert "tag1" == board.tags[0].name
        assert "tag2" == board.tags[1].name

    def test_board_statistics(self, mk_user):
        user = mk_user(email="someuser@mail.com")
        user2 = mk_user(email="someuser2@mail.com")
        board = Board.objects.create(slug="board", owner=user, description="board")
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
