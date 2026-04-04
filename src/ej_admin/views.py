from django.shortcuts import render

from ej_boards.models import Board
from ej_users.models import User
from ej_conversations.models import Conversation
from django.core.paginator import Paginator
from django.contrib.auth.decorators import permission_required
from .utils import (
    PAGINATOR_START_PAGE,
    PAGE_ELEMENTS_COUNT,
    NUM_ENTRIES_DEFAULT,
)

from .utils import (
    apply_user_filters,
    apply_conversation_filters,
    apply_board_filters,
)


@permission_required("ej.can_access_environment_management")
def index(request):
    boards_count = Board.objects.count()
    conversations_count = Conversation.objects.count()
    users_count = User.objects.count()

    return render(
        request,
        "ej_admin/environment.jinja2",
        {
            "user_boards": Board.objects.filter(owner=request.user),
            "boards_count": boards_count,
            "conversations_count": conversations_count,
            "users_count": users_count,
            "current_page": "administration",
        },
    )


@permission_required("ej.can_access_environment_management")
def recent_boards(request):
    page = int(request.GET.get("page", PAGINATOR_START_PAGE))
    board_is_active = (
        True if request.GET.get("boardIsActive", "true") == "true" else False
    )

    if board_is_active:
        recent_boards = (
            Board.objects.filter(conversation__gte=1)
            .distinct()
            .order_by("-created")
        )
    else:
        recent_boards = Board.objects.order_by("-created")

    paginator = Paginator(recent_boards, PAGE_ELEMENTS_COUNT)
    recent_boards = paginator.get_page(page)
    recent_boards.adjusted_elided_pages = paginator.get_elided_page_range(
        recent_boards.number, on_each_side=1, on_ends=1
    )

    return render(
        request,
        "ej_admin/environment/recent-boards.jinja2",
        {
            "recent_boards": recent_boards,
        },
    )


@permission_required("ej.can_access_environment_management")
def searched_users(request):
    num_entries = request.GET.get("numEntries", NUM_ENTRIES_DEFAULT)
    order_by = request.GET.get("orderBy", "date")
    sort = request.GET.get("sort", "desc")
    search_string = request.GET.get("searchString", "")
    page = int(request.GET.get("page", PAGINATOR_START_PAGE))

    searched_users = apply_user_filters(order_by, sort, search_string)

    paginator = Paginator(searched_users, num_entries)

    page_object = paginator.get_page(page)
    page_object.adjusted_elided_pages = paginator.get_elided_page_range(
        page_object.number, on_each_side=1, on_ends=1
    )

    return render(
        request,
        "ej_admin/environment/searched-users.jinja2",
        {
            "page_object": page_object,
        },
    )


@permission_required("ej.can_access_environment_management")
def searched_boards(request):
    num_entries = request.GET.get("numEntries", NUM_ENTRIES_DEFAULT)
    order_by = request.GET.get("orderBy")
    sort = request.GET.get("sort", "desc")
    search_string = request.GET.get("searchString", "")
    page = int(request.GET.get("page", PAGINATOR_START_PAGE))

    searched_boards = apply_board_filters(order_by, sort, search_string)

    paginator = Paginator(searched_boards, num_entries)

    page_object = paginator.get_page(page)
    page_object.adjusted_elided_pages = paginator.get_elided_page_range(
        page_object.number, on_each_side=1, on_ends=1
    )

    return render(
        request,
        "ej_admin/environment/searched-boards.jinja2",
        {
            "page_object": page_object,
        },
    )


@permission_required("ej.can_access_environment_management")
def searched_conversations(request):
    num_entries = request.GET.get("numEntries", NUM_ENTRIES_DEFAULT)
    order_by = request.GET.get("orderBy")
    sort = request.GET.get("sort", "desc")
    search_string = request.GET.get("searchString", "")
    page = int(request.GET.get("page", PAGINATOR_START_PAGE))

    searched_conversations = apply_conversation_filters(
        order_by, sort, search_string
    )

    paginator = Paginator(searched_conversations, num_entries)

    page_object = paginator.get_page(page)
    page_object.adjusted_elided_pages = paginator.get_elided_page_range(
        page_object.number, on_each_side=1, on_ends=1
    )

    return render(
        request,
        "ej_admin/environment/searched-conversations.jinja2",
        {
            "page_object": page_object,
        },
    )


@permission_required("ej.can_access_environment_management")
def get_favorite_boards(request):
    user = request.user

    favorite_boards = user.favorite_boards.order_by("-created")

    return render(
        request,
        "ej_admin/environment/favorite-boards.jinja2",
        {
            "favorite_boards": favorite_boards,
        },
    )
