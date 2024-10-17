from django.urls import path
from ej_dataviz.views import dataviz, report

app_name = "ej_dataviz"
conversation_url = "<int:conversation_id>/<slug:slug>/"
report_url = "<int:conversation_id>/<slug:slug>/report/"

reports_urlpatterns = [
    path(
        report_url + "comments/",
        report.CommentReportDetailView.as_view(),
        name="comments",
    ),
    path(
        report_url + "comments/filter",
        report.CommentReportFilterView.as_view(),
        name="comments-filter",
    ),
    path(
        report_url + "users/",
        report.UsersReportDetailView.as_view(),
        name="users",
    ),
    path(
        report_url + "users/filter",
        report.UsersReportFilterView.as_view(),
        name="users-filter",
    ),
]

dataviz_urlpatterns = [
    path(
        report_url + "votes-over-time/",
        dataviz.votes_over_time,
        name="votes_over_time",
    ),
    path(
        report_url + "data/votes.<fmt>",
        dataviz.votes_data,
        name="votes_data",
    ),
    path(
        report_url + "data/cluster-<int:cluster_id>/votes.<fmt>",
        dataviz.votes_data_cluster,
        name="votes_data_cluster",
    ),
    path(
        report_url + "data/users.<fmt>",
        dataviz.users_data,
        name="users_data",
    ),
    path(
        report_url + "data/comments.<fmt>",
        dataviz.comments_data,
        name="comments_data",
    ),
    path(
        conversation_url + "dashboard/",
        dataviz.ConversationDashboardView.as_view(),
        name="dashboard",
    ),
    path(
        conversation_url + "dashboard/cluster",
        dataviz.ClusterDetailView.as_view(),
        name="cluster-detail",
    ),
    path(
        conversation_url + "scatter/",
        dataviz.scatter,
        name="scatter",
    ),
    path(
        conversation_url + "scatter/pca.json/",
        dataviz.scatter_pca_json,
        name="scatter_pca_json",
    ),
    path(
        conversation_url + "scatter/group-<groupby>.json",
        dataviz.scatter_group,
        name="scatter_group",
    ),
    path(
        conversation_url + "dashboard/words.json",
        dataviz.words,
        name="words",
    ),
]

urlpatterns = [*dataviz_urlpatterns, *reports_urlpatterns]
