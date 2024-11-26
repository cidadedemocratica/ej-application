import json
from django.core.paginator import Paginator
from django.shortcuts import render
from django.views.generic import DetailView
from sidekick import import_later

from ej.decorators import can_access_dataviz_class_view
from ej_conversations.models import Conversation, Comment
from ej_dataviz.utils import get_clusters, get_comments_dataframe, get_user_dataframe
from ej_dataviz.views.filters import (
    CommentsReportClustersFilter,
    CommentsReportSearchFilter,
    ReportOrderByFilter,
    UsersReportClustersFilter,
    UsersReportSearchFilter,
)

pd = import_later("pandas")


class ReportsBaseView(DetailView):
    """
    Common implementation for a conversation reports.
    """

    model = Conversation

    def get_dataframe(self, conversation: Conversation):
        pass

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        conversation = context["object"]
        clusters = get_clusters(conversation)
        context["clusters"] = clusters

        dataframe = self.get_dataframe(conversation)
        context["page"] = self.paginate(dataframe, self.request.GET.get("page") or 1)
        return context

    @can_access_dataviz_class_view
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)

    def paginate(
        self,
        df=pd.DataFrame(),
        page_number: int = 1,
        page_size: int = 10,
    ):
        """
        creates a Django Paginator instance using dataframe rows.

        :param page_number: a integer with the Paginator page.
        :param conversation: a Conversation instance
        """
        dataframe_rows = df.values
        if len(dataframe_rows) > 0:
            paginator = Paginator(dataframe_rows, page_size)
            return paginator.get_page(page_number)
        return Paginator(dataframe_rows, 1).page(1)


class CommentReportFilterView(ReportsBaseView):
    """
    Returns conversation comments based on filter params.
    """

    model = Conversation
    template_name = "ej_dataviz/reports/includes/comments/table.jinja2"

    def get_dataframe(self, conversation):
        return get_comments_dataframe(conversation, "")

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        conversation = context["object"]
        search_text = self.request.GET.get("search")
        order_by = self.request.GET.get("order-by")
        ascending = self.request.GET.get("sort", False) == "asc"

        cluster_ids = self.request.GET.getlist("clusters")
        comments_df = CommentsReportClustersFilter(
            cluster_ids=cluster_ids, conversation=conversation
        ).filter()
        comments_df = CommentsReportSearchFilter(search_text, comments_df).filter()
        comments_df = ReportOrderByFilter(
            order_by, comments_df, ascending, "comment"
        ).filter()
        comments_df = comments_df.reset_index()

        context["page"] = self.paginate(comments_df, self.request.GET.get("page") or 1)
        context["comments"] = json.dumps(comments_df.to_json(orient="records"))
        return context


class CommentReportDetailView(ReportsBaseView):
    """
    Returns comment report page.
    """

    template_name = "ej_dataviz/reports/comments.jinja2"

    def get_dataframe(self, conversation):
        comments_df = get_comments_dataframe(conversation, "")
        comments_df = comments_df.reset_index()
        return comments_df

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        conversation = context["object"]
        dataframe = self.get_dataframe(conversation)
        context["comments"] = json.dumps(dataframe.to_json(orient="records"))
        return context


class CommentDetailView(DetailView):
    """
    Returns comment report page.
    """

    template_name = "ej_dataviz/reports/includes/comments/modal.jinja2"
    model = Comment

    def post(self, *args, **kwargs):
        context = self.get_context_data()
        return render(self.request, self.template_name, context)

    def get_context_data(self, *args, **kwargs):
        comment = self.get_object()
        comment_index = int(self.request.POST["current_index"][0])
        comments = json.loads(self.request.POST["comments"])

        return {
            "comment": comment,
            "comments": json.dumps(self.request.POST["comments"]),
            "comment_statistics": comments[comment_index],
            "previous_id": comment.previous(comment_index, comments),
            "next_id": comment.next(comment_index, comments),
            "current_index": comment_index,
        }


class UsersReportDetailView(ReportsBaseView):
    """
    Returns user report page.
    """

    template_name = "ej_dataviz/reports/users.jinja2"
    model = Conversation

    def get_dataframe(self, conversation):
        return get_user_dataframe(conversation)


class UsersReportFilterView(ReportsBaseView):
    """
    Returns conversation users based on filter params.
    """

    model = Conversation
    template_name = "ej_dataviz/reports/includes/users/table.jinja2"

    def get_dataframe(self, conversation):
        return get_user_dataframe(conversation)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        conversation = context["object"]
        search_text = self.request.GET.get("search")
        order_by = self.request.GET.get("order-by")
        ascending = self.request.GET.get("sort", False) == "asc"
        cluster_ids = self.request.GET.getlist("clusters")
        users_df = UsersReportClustersFilter(cluster_ids, conversation).filter()
        users_df = UsersReportSearchFilter(search_text, users_df).filter()
        users_df = ReportOrderByFilter(order_by, users_df, ascending, "name").filter()
        context["page"] = self.paginate(users_df, self.request.GET.get("page") or 1)
        return context
