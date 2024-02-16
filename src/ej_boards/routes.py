from boogie.router import Router
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _

from ej_boards.models import Board
from ej_boards.utils import patched_register_app_routes
from ej_clusters.models import Stereotype
from ej_conversations.models import Conversation
from ej_tools.urls import urlpatterns as conversation_tools_urlpatterns
from ej_conversations.urls.conversations import urlpatterns as conversation_urlpatterns, conversation_url
from ej_clusters.urls.clusters import urlpatterns as cluster_urlpatterns
from ej_dataviz.urls import urlpatterns as dataviz_urlpatterns
from .forms import BoardForm
from ej_tools.models import RasaConversation, ConversationMautic

app_name = "ej_boards"
urlpatterns = Router(
    template=["ej_boards/{name}.jinja2", "generic.jinja2"],
    models={
        "board": Board,
        "conversation": Conversation,
        "stereotype": Stereotype,
        "connection": RasaConversation,
        "mautic_connection": ConversationMautic,
    },
    lookup_field={"board": "slug"},
    lookup_type={"board": "slug"},
)

# Constants
board_profile_admin_url = "profile/boards/"
board_base_url = "<model:board>/conversations/"
board_conversation_url = board_base_url + conversation_url
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
        return redirect(f"{boards[0].get_absolute_url()}")

    return {"boards": boards, "can_add_board": can_add_board}


@urlpatterns.route(board_profile_admin_url + "add/", login=True)
def board_create(request):  # TODO arrumar o navigation dele
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
    return {"form": form, "board": board, "user_boards": Board.objects.filter(owner=request.user)}


#
# Conversation URLs
#
@urlpatterns.route("<model:board>/")
def board_base(request, board):
    return redirect(board.get_absolute_url())


#   When app uses django views, we use patched_register_app_routes
#
patched_register_app_routes(urlpatterns.urls, conversation_tools_urlpatterns, "conversation-tools")
patched_register_app_routes(urlpatterns.urls, conversation_urlpatterns, "conversation")
patched_register_app_routes(urlpatterns.urls, cluster_urlpatterns, "cluster")
patched_register_app_routes(urlpatterns.urls, dataviz_urlpatterns, "dataviz")
