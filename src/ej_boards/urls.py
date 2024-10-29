from django.urls import path

from ej_boards.utils import patched_register_app_routes
from ej_clusters.urls.clusters import urlpatterns as cluster_urlpatterns
from ej_clusters.urls.stereotype_votes import urlpatterns as stereotype_votes_urlpatterns
from ej_conversations.urls.conversations import urlpatterns as conversation_urlpatterns
from ej_dataviz.urls import urlpatterns as dataviz_urlpatterns
from ej_integrations.urls import urlpatterns as conversation_tools_urlpatterns

from . import views

app_name = "ej_boards"
conversation_url = "<int:conversation_id>/<slug:slug>"

urlpatterns = [
    path(
        "profile/boards/",
        views.BoardListView.as_view(),
        name="board-list",
    ),
    path(
        "profile/boards/add/",
        views.BoardCreateView.as_view(),
        name="board-create",
    ),
    path(
        "<slug:board_slug>/edit/",
        views.BoardEditView.as_view(),
        name="board-edit",
    ),
    path(
        "<slug:board_slug>/",
        views.BoardBaseView.as_view(),
        name="board-base",
    ),
    path(
        "<slug:board_slug>/delete/",
        views.BoardDeleteView.as_view(),
        name="board-delete",
    ),
]

#   When app uses django views, we use patched_register_app_routes
#
patched_register_app_routes(
    urlpatterns, conversation_tools_urlpatterns, "conversation-tools"
)
patched_register_app_routes(urlpatterns, conversation_urlpatterns, "conversation")
patched_register_app_routes(urlpatterns, cluster_urlpatterns, "cluster")
patched_register_app_routes(urlpatterns, stereotype_votes_urlpatterns, "stereotype-votes")
patched_register_app_routes(urlpatterns, dataviz_urlpatterns, "dataviz")
