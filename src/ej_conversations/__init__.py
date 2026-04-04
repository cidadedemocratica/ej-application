from .enums import Choice

default_app_config = "ej_conversations.apps.EjConversationsConfig"


def create_conversation(
    text,
    title,
    author,
    board=None,
    *,
    is_promoted=False,
    tags=(),
    commit=True,
    **kwargs
):
    """
    Creates a new conversation object and saves it in the database.
    """
    from .models import Conversation
    from django.contrib.auth import get_user_model

    if not board:
        User = get_user_model()
        board = User.create_user_default_board(author)

    conversation = Conversation(
        text=text,
        title=title,
        author=author,
        board=board,
        is_promoted=is_promoted,
        **kwargs,
    )
    conversation.clean()
    if commit:
        conversation.save()
    if tags:
        conversation.tags.set(tags.split(","))
    return conversation
