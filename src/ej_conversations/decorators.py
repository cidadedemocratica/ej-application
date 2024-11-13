from django.shortcuts import redirect, reverse

from ej_conversations.models.conversation import Conversation
from ej_conversations.utils import get_htmx_redirect_response
from ej_users.models import User


def bot_tool_is_active(bots_tool, tool_name):
    """
    checks if a certain type of bot (webchat, telegram, whatsapp) is active.
    """
    tool = getattr(bots_tool, tool_name)
    return tool.is_active


def redirect_to_conversation_detail(view):
    """
    Verify if request.user should see the welcome page.
    If not, redirect  him to conversation detail route.
    """

    def wrapper(self, request, *args, **kwargs):
        user = request.user
        conversation = self.get_object()
        user_has_votes = conversation.votes.filter(author__id=user.id).exists()
        user_has_comments = conversation.comments.filter(author__id=user.id).exists()
        if user_has_votes or user_has_comments or not conversation.welcome_message:
            return redirect("boards:conversation-detail", **conversation.get_url_kwargs())
        return view(self, request, *args, **kwargs)

    return wrapper


def user_can_post_anonymously(func):
    """
    user_can_post_anonymously checks if conversation was configured to accept
    anonymous votes.
    """

    def wrapper(self, request, conversation_id, slug, board_slug, *args, **kwargs):
        conversation: Conversation = self.get_object()
        request.user = User.get_or_create_from_session(conversation, request)
        redirect_url = ""
        register_url = reverse("auth:register")
        conversation_url = reverse(
            "boards:conversation-detail", kwargs=conversation.get_url_kwargs()
        )
        next_param = f"next={conversation_url}"
        session_param = f"sessionKey={request.session.session_key}"

        if conversation.reaches_anonymous_particiption_limit(request.user):
            redirect_url = f"{register_url}?{session_param}&{next_param}"
        elif request.user.is_anonymous:
            redirect_url = f"{register_url}?{next_param}"

        if redirect_url:
            return get_htmx_redirect_response(redirect_url)

        return func(self, request, conversation_id, slug, board_slug, *args, **kwargs)

    return wrapper


def create_session_key(func):
    """
    create_session_key check if request.session.session_key is empty.
    If so, creates it.
    """

    def wrapper(self, **kwargs):
        User.creates_request_session_key(self.request)
        return func(self)

    return wrapper
