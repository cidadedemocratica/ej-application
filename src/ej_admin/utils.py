from inspect import Signature
from django.urls import path
from django.db.models import Count, Q
from ej_users.models import User

from django.http import Http404


PAGINATOR_START_PAGE = 1
PAGE_ELEMENTS_COUNT = 12
NUM_ENTRIES_DEFAULT = 6

MAX_PAGINATOR_ITEMS = 7
ELLIPSE_LIMIT = 5


class OrderByOptions:
    DATE = "date"
    CONVERSATION = "conversations-count"
    COMMENT = "comments-count"


def register_route(router, route, base_path, prefix):
    """
    Register copy of route in the given router object.
    """
    templates = route.template
    if isinstance(templates, (list, tuple)):
        templates = templates[0]
    if isinstance(templates, str):
        template_prefix, _, data = templates.partition("/")
        if template_prefix.startswith("ej_"):
            template_prefix = template_prefix[3:]
        templates = f"ej_boards/{template_prefix}-{data}"

    return router.register(
        make_view(route.function),
        path=base_path + route.path,
        name=prefix + "-" + route.name,
        login=route.login,
        perms=route.perms,
        template=templates,
    )


def make_view(view):
    if "request" in Signature.from_callable(view).parameters:
        return lambda request, board, **kwargs: view(
            request, board=board, **kwargs
        )
    else:
        return lambda **kwargs: view(**kwargs)


def assure_correct_board(conversation, board):
    """
    Raise 404 if conversation does not belong to board.
    """
    if not board.has_conversation(conversation):
        raise Http404
    conversation.board = board


def check_board(board):
    """
    Raise 404 if conversation does not belong to board.
    """

    def check_function(conversation, request):
        if not board.has_conversation(conversation):
            raise Http404
        if conversation.is_hidden and not request.user.has_perm(
            "ej.can_edit_conversation", conversation
        ):
            raise Http404
        conversation.board = board
        return conversation

    return check_function


def register_app_routes(app_routes, board_base_url, urlpatterns, route_name):
    base_path = board_base_url + app_routes.urlpatterns.base_path
    for route in app_routes.urlpatterns.routes:
        register_route(urlpatterns, route, base_path, route_name)


def patched_register_app_routes(
    board_urls, app_urls, app_name, url_path="<slug:board_slug>/conversations/"
):
    """
    Register an app's routes in the boards namespace using django's default routes, not boogie's.
    """
    for url in app_urls:
        board_url = url_path + str(url.pattern)
        view = url.callback
        pattern = path(board_url, view, name=f"{app_name}-{url.name}")
        board_urls.append(pattern)
    return board_urls


def statistics(board):
    """
    Return a dictionary with basic statistics about board.
    """
    votes = 0
    participants = 0
    conversations = 0

    for conversation in board.conversations:
        stats = conversation.statistics()
        votes += stats["votes"]["total"]
        participants += stats["participants"]["voters"]
        conversations += 1

    return {
        "votes": votes,
        "participants": participants,
        "conversations": conversations,
    }


def apply_user_filters(order_by, sort, search_string):
    sort_order = "-" if sort == "desc" else ""

    if order_by == OrderByOptions.CONVERSATION:
        searched_users = User.objects.annotate(
            count=Count("conversations")
        ).order_by(f"{sort_order}count")
    elif order_by == OrderByOptions.COMMENT:
        searched_users = User.objects.annotate(
            count=Count("comments")
        ).order_by(f"{sort_order}count")
    else:
        searched_users = User.objects.order_by(f"{sort_order}date_joined")

    if search_string:
        searched_users = searched_users.filter(
            Q(email__icontains=search_string) | Q(name__icontains=search_string)
        )

    # will return a list, as returning a UserQuerySet brings inconsistent results in Paginator
    searched_users = list(searched_users)

    return searched_users


def apply_conversation_filters(order_by, sort, search_string):
    from ej_conversations.models import Conversation

    sort_order = "-" if sort == "desc" else ""

    if order_by == OrderByOptions.COMMENT:
        searched_conversations = Conversation.objects.annotate(
            count=Count("comments")
        ).order_by(f"{sort_order}count")
    else:
        searched_conversations = Conversation.objects.order_by(
            f"{sort_order}created"
        )

    if search_string:
        searched_conversations = searched_conversations.filter(
            Q(title__icontains=search_string)
            | Q(author__name__icontains=search_string)
            | Q(slug__icontains=search_string)
        )

    return searched_conversations


def apply_board_filters(order_by, sort, search_string):
    from ej_boards.models import Board

    sort_order = "-" if sort == "desc" else ""

    if order_by == OrderByOptions.CONVERSATION:
        searched_boards = Board.objects.annotate(
            count=Count("conversation")
        ).order_by(f"{sort_order}count")
    elif order_by == OrderByOptions.COMMENT:
        searched_boards = Board.objects.annotate(
            count=Count("conversation__comments")
        ).order_by(f"{sort_order}count")
    else:
        searched_boards = Board.objects.order_by(f"{sort_order}created")

    if search_string:
        searched_boards = searched_boards.filter(
            Q(owner__email__icontains=search_string)
            | Q(owner__name__icontains=search_string)
            | Q(title__icontains=search_string)
            | Q(slug__icontains=search_string)
        )
        pass

    return searched_boards
