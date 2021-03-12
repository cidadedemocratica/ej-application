from boogie.router import Router
from django.apps import apps
from django.shortcuts import redirect
from django.utils.translation import ugettext_lazy as _

from ej_boards.models import Board
from ej_boards.utils import check_board, register_route
from ej_clusters.models import Stereotype
from ej_conversations import routes as conversations
from ej_conversations.models import Conversation
from ej_conversations.tools import routes as tools_routes
from .forms import BoardForm

app_name = "ej_boards"
urlpatterns = Router(
    template=["ej_boards/{name}.jinja2", "generic.jinja2"],
    models={"board": Board, "conversation": Conversation, "stereotype": Stereotype},
    lookup_field={"board": "slug"},
    lookup_type={"board": "slug"},
)

# Constants
board_profile_admin_url = "profile/boards/"
board_base_url = "<model:board>/conversations/"
board_conversation_url = board_base_url + "<model:conversation>/<slug:slug>/"
reports_url = "<model:board>/conversations/<model:conversation>/reports/"
reports_kwargs = {"login": True}

#
# Board URLs
#
@urlpatterns.route(board_profile_admin_url, login=True)
def board_list(request):
    user = request.user
    boards = user.boards.all()
    can_add_board = user.has_perm("ej.can_add_board")

    # Redirect to user's unique board, if that is the case
    if not can_add_board and user.boards.count() == 1:
        return redirect(f"{boards[0].get_absolute_url()}conversations/")

    return {"boards": boards, "can_add_board": can_add_board}


@urlpatterns.route(board_profile_admin_url + "add/", login=True, perms=["ej.can_add_board"])
def board_create(request):
    form = BoardForm(request=request)
    if form.is_valid_post():
        board = form.save(owner=request.user)
        return redirect(board.get_absolute_url())
    return {"form": form}


@urlpatterns.route("<model:board>/edit/", perms=["ej.can_edit_board:board"])
def board_edit(request, board):
    form = BoardForm(instance=board, request=request)
    form.fields["slug"].help_text = _("You cannot change this value")
    form.fields["slug"].disabled = True

    if form.is_valid_post():
        form.save()
        return redirect(board.get_absolute_url())
    return {"form": form, "board": board}


#
# Conversation URLs
#
@urlpatterns.route("<model:board>/")
def board_base(request, board):
    return redirect(board.get_absolute_url())


@urlpatterns.route(board_base_url)
def conversation_list(request, board):
    return conversations.list_view(
        request, 
        queryset=board.conversations.annotate_attr(board=board), 
        context={"board": board}, 
        title=board.title,
    )


@urlpatterns.route(board_base_url + "add/", perms=["ej.can_edit_board:board"])
def conversation_create(request, board):
    return conversations.create(request, board=board, context={"board": board})


@urlpatterns.route(board_conversation_url, login=True)
def conversation_detail(request, board, **kwargs):
    return conversations.detail(request, **kwargs, check=check_board(board))


@urlpatterns.route(board_conversation_url + "edit/", perms=["ej.can_edit_conversation:conversation"])
def conversation_edit(request, board, **kwargs):
    return conversations.edit(request, board=board, check=check_board(board), **kwargs)


@urlpatterns.route(board_conversation_url + "moderate/", perms=["ej.can_edit_conversation:conversation"])
def conversation_moderate(request, board, **kwargs):
    return conversations.moderate(request, check=check_board(board), **kwargs)


@urlpatterns.route(board_conversation_url + "integrations/")
def conversation_integrations(request, board, **kwargs):
    return conversations.integrations(request,  check=check_board(board), **kwargs)


@urlpatterns.route(board_conversation_url + "tools/", perms=["ej.can_edit_conversation:conversation"])
def conversation_tools_index(request, board, **kwargs):
    check_board(board)
    return tools_routes.index(request, **kwargs)


@urlpatterns.route(board_conversation_url + "tools/mailing/", perms=["ej.can_edit_conversation:conversation"])
def conversation_tools_mailing(request, board, **kwargs):
    check_board(board)
    return tools_routes.mailing(request, **kwargs)


@urlpatterns.route(board_conversation_url + "tools/component/", perms=["ej.can_edit_conversation:conversation"])
def conversation_tools_component(request, board, **kwargs):
    check_board(board)
    return tools_routes.conversation_component(request, **kwargs)


@urlpatterns.route(board_conversation_url + "tools/rasa/", perms=["ej.can_edit_conversation:conversation"])
def conversation_tools_rasa(request, board, **kwargs):
    check_board(board)
    return tools_routes.rasa(request, **kwargs)


#
# Dataviz
#
if apps.is_installed("ej_dataviz"):
    from ej_dataviz import routes as dataviz
    from ej_dataviz import routes_report as report

    base_path = board_base_url + dataviz.urlpatterns.base_path
    for route in dataviz.urlpatterns.routes:
        register_route(urlpatterns, route, base_path, "dataviz")

    base_path = board_base_url + report.urlpatterns.base_path
    for route in report.urlpatterns.routes:
        register_route(urlpatterns, route, base_path, "report")

#
# Clusters
#
if apps.is_installed("ej_clusters"):
    from ej_clusters import routes as cluster

    base_path = board_base_url + cluster.urlpatterns.base_path
    for route in cluster.urlpatterns.routes:
        register_route(urlpatterns, route, base_path, "cluster")
