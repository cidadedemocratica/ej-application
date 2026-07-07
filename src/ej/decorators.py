from django.shortcuts import redirect
from ej_boards.models import Board
from ej_conversations.models.conversation import Conversation
from django.http import JsonResponse


def can_edit_conversation(view_func):
    def wrapper_func(request, *args, **kwargs):
        try:
            conversation_id = kwargs.get("conversation_id")
            conversation = Conversation.objects.get(id=conversation_id)
        except (AttributeError, Conversation.DoesNotExist):
            return redirect("auth:login")

        if request.user.has_perm("ej.can_edit_conversation", conversation):
            return view_func(request, *args, **kwargs)
        return redirect("auth:login")

    return wrapper_func


def can_delete_conversation(view_func):
    def wrapper_func(request, *args, **kwargs):
        try:
            conversation_id = kwargs.get("conversation_id")
            conversation = Conversation.objects.get(id=conversation_id)
        except (AttributeError, Conversation.DoesNotExist):
            return redirect("auth:login")

        if request.user.has_perm("ej.can_delete_conversation", conversation):
            return view_func(request, *args, **kwargs)
        return redirect("auth:login")

    return wrapper_func


def can_access_tool_page(view_func):
    """
    Can access a tool page from a conversation.

    * User is staff
    * OR user is an superuser
    * OR user is the conversation author
    * OR user is an invited conversation manager
    """

    def wrapper_func(request, *args, **kwargs):
        try:
            conversation_id = kwargs.get("conversation_id")
            conversation = Conversation.objects.get(id=conversation_id)
        except (AttributeError, Conversation.DoesNotExist):
            return redirect("auth:login")
        if request.user.has_perm("ej.can_access_tools_page", conversation):
            return view_func(request, *args, **kwargs)
        return redirect("auth:login")

    return wrapper_func


def can_moderate_conversation(view_func):
    def wrapper_func(request, *args, **kwargs):
        try:
            conversation_id = kwargs.get("conversation_id")
            conversation = Conversation.objects.get(id=conversation_id)
        except (AttributeError, Conversation.DoesNotExist):
            return redirect("auth:login")

        if request.user.has_perm("ej.can_moderate_conversation", conversation):
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
        except (AttributeError, Conversation.DoesNotExist):
            return redirect("auth:login")

        if request.user.has_perm("ej.can_access_dataviz", conversation):
            return view_func(self, request, *args, **kwargs)
        return redirect("auth:login")

    return wrapper_func


def can_access_dataviz(view_func):
    def wrapper_func(request, *args, **kwargs):
        try:
            conversation_id = kwargs.get("conversation_id")
            conversation = Conversation.objects.get(id=conversation_id)
        except (AttributeError, Conversation.DoesNotExist):
            return redirect("auth:login")

        if request.user.has_perm("ej.can_access_dataviz", conversation):
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
