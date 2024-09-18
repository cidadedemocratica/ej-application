from django.urls import path
from ..views import stereotype_votes


app_name = "ej_clusters"
conversation_url = "<int:conversation_id>/<slug:slug>/"


urlpatterns = [
    path(
        conversation_url + "stereotypes/",
        stereotype_votes.StereotypeVotesView.as_view(),
        name="list",
    ),
    path(
        conversation_url + "stereotypes/stereotype-votes/<int:pk>/manage",
        stereotype_votes.StereotypeVotesManageView.as_view(),
        name="manage",
    ),
]
