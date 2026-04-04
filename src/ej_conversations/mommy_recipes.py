from model_mommy.recipe import Recipe, foreign_key as _foreign_key
from sidekick import record
from ej_boards.mommy_recipes import BoardRecipes

from ej.testing import EjRecipes
from ej_conversations.enums import Choice
from .models import Comment, Conversation, Vote

__all__ = ["ConversationRecipes"]


class ConversationRecipes(BoardRecipes):
    conversation = Recipe(
        Conversation,
        title="Conversation",
        text="question?",
        slug="conversation",
        is_promoted=True,
        author=_foreign_key(EjRecipes.author),
    )
    comment = Recipe(
        Comment,
        author=_foreign_key(
            EjRecipes.author.extend(email="comment_author@domain.com")
        ),
        content="comment",
        conversation=_foreign_key(conversation),
        status=Comment.STATUS.approved,
    )
    vote = Recipe(
        Vote,
        comment=_foreign_key(comment),
        author=_foreign_key(EjRecipes.author.extend(email="voter@domain.com")),
        choice=Choice.AGREE,
    )

    def get_data(self, request):
        data = super().get_data(request)
        conversation = self.conversation.make(
            author=data.author, board=data.board
        )
        comments = [
            self.comment.make(
                author=data.author,
                conversation=conversation,
                content="comment-author",
            ),
            self.comment.make(author=data.user, conversation=conversation),
        ]
        votes = [
            self.vote.make(comment=comment, author=data.user)
            for comment in comments
        ]
        return record(
            data, conversation=conversation, comments=comments, votes=votes
        )


ConversationRecipes.update_globals(globals())
