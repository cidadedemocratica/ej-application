from django.db import transaction
from django.utils.translation import gettext_lazy as _


from ej_conversations.forms import CommentForm, ConversationForm
from ej_conversations.models import Comment
from ej_boards.models import Board

from django.core.exceptions import ValidationError
import pytest


class TestConversationForm:
    def test_valid_conversation_form(self, db):
        form = ConversationForm(
            {
                "title": "conversation-slug",
                "tags": "tag",
                "text": "description",
                "comments_count": 1,
                "comment-1": "comment",
                "anonymous_votes": 0,
            }
        )
        assert form.is_valid()

    def test_conversation_form_save(self, db, user):
        board = Board.objects.create(
            slug="board1", owner=user, description="board"
        )
        form = ConversationForm(
            {
                "title": "conversation",
                "tags": "tag",
                "text": "description",
                "comments_count": 1,
                "comment-1": "comment",
                "anonymous_votes": 0,
            }
        )
        assert form.is_valid()
        with transaction.atomic():
            conversation = form.save_comments(
                author=user, is_promoted=True, board=board
            )

        assert conversation
        assert conversation.author == user
        assert conversation.title == "conversation"
        assert conversation.tags.first().name == "tag"
        assert conversation.comments.first().content == "comment"
        assert conversation.comments.first().status == Comment.STATUS.approved
        assert conversation.board == board

    def test_conversation_form_without_board_should_not_be_saved(self):
        with pytest.raises(ValidationError):
            form = ConversationForm(
                {
                    "title": "conversation",
                    "tags": "tag",
                    "text": "description",
                    "comments_count": 1,
                    "comment-1": "comment",
                    "anonymous_votes": 0,
                }
            )
            form.save()

    def test_repeated_comments_error(self, conversation, db, user):
        Comment.objects.create(
            content="comment", conversation=conversation, author=user
        )
        form = CommentForm({"content": "comment"}, conversation=conversation)
        assert not form.is_valid()
        assert (
            _("You already submitted this comment.")
            == form.errors["content"][0]
        )

    def test_xss_injection_is_cleaned(self, db):
        xss_script = "<div><script>testing css</script></div>"
        form = ConversationForm(
            {
                "title": "conversation-slug",
                "tags": "tag",
                "text": "description",
                "comments_count": 1,
                "comment-1": "comment",
                "anonymous_votes": 0,
                "welcome_message": xss_script,
                "ending_message": xss_script,
            }
        )
        assert form.is_valid()
        assert form.cleaned_data["welcome_message"] == "<div></div>"

    def test_xss_dont_clean_normal_html(self, db):
        non_xss_script = "<div><b>Hello!</b></div>"
        form = ConversationForm(
            {
                "title": "conversation-slug",
                "tags": "tag",
                "text": "description",
                "comments_count": 1,
                "comment-1": "comment",
                "anonymous_votes": 0,
                "welcome_message": non_xss_script,
                "ending_message": non_xss_script,
            }
        )
        assert form.is_valid()
        assert form.cleaned_data["welcome_message"] == non_xss_script
