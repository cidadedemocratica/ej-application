from django.shortcuts import redirect
from ej_boards.models import Board
from ej_conversations.models.conversation import Conversation
from django.http import JsonResponse


def can_edit_conversation(view_func):
    def wrapper_func(request, *args, **kwargs):
        try:
            conversation_id = kwargs.get("conversation_id")
            conversation = Conversation.objects.get(id=conversation_id)
        except AttributeError:
            return redirect("auth:login")

        if request.user.id == conversation.author_id:
            return view_func(request, *args, **kwargs)
        elif conversation.is_promoted and request.user.has_perm(
            "ej_conversations.can_publish_promoted"
        ):
            return view_func(request, *args, **kwargs)
        return redirect("auth:login")

    return wrapper_func


def can_access_tool_page(view_func):
    """
    Can access a tool page from a conversation.

    * User is staff
    * OR user is an superuser
    * OR user is the conversation author
    """

    def wrapper_func(request, *args, **kwargs):
        try:
            conversation_id = kwargs.get("conversation_id")
            conversation = Conversation.objects.get(id=conversation_id)
        except AttributeError:
            return redirect("auth:login")
        if (
            request.user.is_staff
            or request.user.is_superuser
            or conversation.author.id == request.user.id
        ):
            return view_func(request, *args, **kwargs)
        return redirect("auth:login")

    return wrapper_func


def can_moderate_conversation(view_func):
    def wrapper_func(request, *args, **kwargs):
        try:
            conversation_id = kwargs.get("conversation_id")
            conversation = Conversation.objects.get(id=conversation_id)
        except AttributeError:
            return redirect("auth:login")

        if request.user.id == conversation.author_id:
            return view_func(request, *args, **kwargs)
        elif conversation.is_promoted and request.user.has_perm(
            "ej_conversations.can_moderate_conversation"
        ):
            return view_func(request, *args, **kwargs)
        return redirect("auth:login")

    return wrapper_func


def can_acess_list_view(view_func):
    def wrapper_func(request, *args, **kwargs):
        board = Board.objects.get(slug=kwargs["board_slug"])
        if request.user == board.owner:
            return view_func(request, *args, **kwargs)
        if request.user.is_staff or request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        return redirect("auth:login")

    return wrapper_func


def is_superuser(view_func):
    def wrapper_func(request, *args, **kwargs):
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        return redirect("auth:login")

    return wrapper_func


def can_access_dataviz_class_view(view_func):
    def wrapper_func(self, request, *args, **kwargs):
        try:
            conversation_id = kwargs.get("conversation_id")
            conversation = Conversation.objects.get(id=conversation_id)
        except AttributeError:
            return redirect("auth:login")

        is_superuser = request.user.is_staff or request.user.is_superuser
        is_author = request.user.id == conversation.author_id
        is_promoted = conversation.is_promoted and request.user.has_perm(
            "ej_conversations.can_publish_promoted"
        )

        if is_superuser or is_author or is_promoted:
            return view_func(self, request, *args, **kwargs)
        return redirect("auth:login")

    return wrapper_func


def can_access_dataviz(view_func):
    def wrapper_func(request, *args, **kwargs):
        try:
            conversation_id = kwargs.get("conversation_id")
            conversation = Conversation.objects.get(id=conversation_id)
        except AttributeError:
            return redirect("auth:login")

        is_superuser = request.user.is_staff or request.user.is_superuser
        is_author = request.user.id == conversation.author_id
        is_promoted = conversation.is_promoted and request.user.has_perm(
            "ej_conversations.can_publish_promoted"
        )

        if is_superuser or is_author or is_promoted:
            return view_func(request, *args, **kwargs)
        return redirect("auth:login")

    return wrapper_func


def can_view_report_details(view_func):
    def wrapper_func(request, *args, **kwargs):
        try:
            conversation_id = kwargs.get("conversation_id")
            Conversation.objects.get(id=conversation_id)
        except AttributeError:
            return JsonResponse(
                {"error": "You don't have permission to view this data."}
            )

        if (
            request.user.id
            or request.user.is_staff
            or request.user.is_superuser
        ):
            return view_func(request, *args, **kwargs)
        return JsonResponse(
            {"error": "You don't have permission to view this data."}
        )

    return wrapper_func


def check_conversation_overdue(view_func):
    def wrapper_func(request, *args, **kwargs):
        conversation_id = kwargs.get("conversation_id")
        conversation = Conversation.objects.get(id=conversation_id)
        conversation.set_overdue()
        return view_func(request, *args, **kwargs)

    return wrapper_func


def can_edit_board(view_func):
    def wrapper_func(request, *args, **kwargs):
        try:
            user = request.user
            board_slug = kwargs.get("board_slug")
            board = Board.objects.get(slug=board_slug)
        except AttributeError:
            return redirect("auth:login")

        if user == board.owner:
            return view_func(request, *args, **kwargs)
        return redirect("auth:login")

    return wrapper_func
