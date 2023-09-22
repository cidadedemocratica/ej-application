from ej_tools.tools import BotsTool
from ej_users.models import SignatureFactory
from ej_conversations.models.vote import VoteChannels
from rest_framework.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _
from django.shortcuts import redirect


TOOLS_CHANNEL = {
    "socketio": (_("Opinion Bots"), "webchat"),
    "telegram": (_("Opinion Bots"), "telegram"),
    "twilio": (_("Opinion Bots"), "whatsapp"),
    "opinion_component": (_("Opinion component"),),
    "rocketchat": (_("Rocket.Chat"),),
    "unknown": (),
}


def bot_tool_is_active(bots_tool, tool_name):
    """
    checks if a certain type of bot (webchat, telegram, whatsapp) is active.
    """
    tool = getattr(bots_tool, tool_name)
    return tool.is_active


def conversation_can_receive_channel_vote(func):
    """
    Checks if conversation is allowed to receive votes from a given channel (tool).
    If  conversation author signature does not have permission, a 403 error is raised.
    """

    def wrapper_func(self, request, vote):
        if vote.channel == VoteChannels.UNKNOWN:
            raise PermissionDenied(
                {"message": "conversation author can not receive votes from an unknown tool"}
            )

        try:
            conversation = vote.comment.conversation
            author_signature = SignatureFactory.get_user_signature(conversation.author)
            tool_channel = TOOLS_CHANNEL[vote.channel]
            tool = author_signature.get_tool(tool_channel[0], conversation)
        except Exception:
            raise PermissionDenied({"message": f"{vote.channel} tool was not found"})

        if not tool.is_active:
            raise PermissionDenied(
                {"message": f"{vote.channel} is not available on conversation author signature"}
            )
        if type(tool) == BotsTool and not bot_tool_is_active(tool, tool_channel[1]):
            raise PermissionDenied(
                {"message": f"{vote.channel} is not available on conversation author signature"}
            )

        return func(self, request, vote)

    return wrapper_func


def user_can_post_anonymously(func):
    """
    user_can_post_anonymously checks if conversation was configured to accept
    anonymous votes.
    """

    def wrapper(self, request, conversation_id, slug, board_slug, *args, **kwargs):
        conversation = self.get_object()
        request.user = self._get_user()
        if conversation.reaches_anonymous_particiption_limit(request.user):
            return redirect(f"/register/?sessionKey={request.session.session_key}&next={request.path}")
        elif request.user.is_anonymous:
            return redirect(f"/register/?next={request.path}")
        return func(self, request, conversation_id, slug, board_slug, *args, **kwargs)

    return wrapper


def create_session_key(func):
    """
    create_session_key check if request.session.session_key is empty.
    If so, creates it.
    """

    def wrapper(self, **kwargs):
        if not self.request.session.session_key:
            self.request.session.create()
        return func(self)

    return wrapper
