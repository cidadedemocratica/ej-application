import datetime
import json

from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.translation import gettext
import pytest

from ej.testing import UrlTester
from ej_clusters.enums import ClusterStatus
from ej_clusters.models.cluster import Cluster
from ej_clusters.models.clusterization import Clusterization
from ej_clusters.models.stereotype import Stereotype
from ej_clusters.models.stereotype_vote import StereotypeVote
from ej_conversations.enums import Choice
from ej_conversations.mommy_recipes import ConversationRecipes
from ej_dataviz.utils import get_comments_dataframe, get_user_dataframe
from ej_dataviz.views.filters import (
    CommentsReportClustersFilter,
    CommentsReportSearchFilter,
    ReportOrderByFilter,
    UsersReportClustersFilter,
    UsersReportSearchFilter,
)

BASE_URL = "/api/v1"


class TestRoutes(ConversationRecipes, UrlTester):
    admin_urls = [
        "/conversations/1/conversation/report/users/",
        "/conversations/1/conversation/report/comments/",
        "/conversations/1/conversation/dashboard/",
    ]


class TestClusterDetailView:
    def test_cluster_detail_view_bad_request(self, cluster, logged_client):
        conversation = cluster.conversation
        url = reverse(
            "dataviz:cluster-detail",
            kwargs={"conversation_id": conversation.id, "slug": conversation.slug},
        )
        with pytest.raises(ValidationError) as validation_error:
            logged_client.get(url)
        assert (
            validation_error.value.args[0]
            == "cluster_id parameter was not passed to ClusterDetailView"
        )

    def test_cluster_detail_view_with_wrong_cluster_id(self, cluster, logged_client):
        conversation = cluster.conversation
        url = reverse(
            "dataviz:cluster-detail",
            kwargs={
                "conversation_id": conversation.id,
                "slug": conversation.slug,
            },
        )
        with pytest.raises(ValidationError) as validation_error:
            logged_client.get(url, {"cluster_id": "123456789"})
        assert (
            validation_error.value.args[0] == "could not find cluster with id 123456789"
        )

    def test_cluster_detail_view_with_cluster_id(self, cluster, logged_client):
        conversation = cluster.conversation
        url = reverse(
            "dataviz:cluster-detail",
            kwargs={
                "conversation_id": conversation.id,
                "slug": conversation.slug,
            },
        )
        response = logged_client.get(url, {"cluster_id": cluster.id})

        assert response.context["cluster"]
        assert response.context["cluster"].name == cluster.name

        assert response.context["conversation"]
        assert response.context["conversation"].title == conversation.title

        assert response.context["cluster_relevant_agreed_comments"] == []
        assert response.context["cluster_relevant_disagred_comments"] == []


class TestReportRoutes:
    def test_should_get_count_of_votes_in_a_period_of_time(
        self, conversation_with_votes, logged_client
    ):
        conversation = conversation_with_votes
        today = datetime.datetime.now().date()  # 2022-04-04
        one_week_ago = today - datetime.timedelta(days=7)
        url = reverse(
            "boards:dataviz-votes_over_time", kwargs=conversation.get_url_kwargs()
        )
        url = url + f"?startDate={one_week_ago}&endDate={today}"
        response = logged_client.get(url)
        data = json.loads(response.content)["data"]

        assert response.status_code == 200
        assert len(data) == 8
        assert data[0]["date"] == one_week_ago.strftime("%Y-%m-%dT%H:%M:%SZ")
        assert data[-1]["date"] == today.strftime("%Y-%m-%dT%H:%M:%SZ")

        assert data[0]["value"] == 0
        assert data[1]["value"] == 0
        assert data[2]["value"] == 0
        assert data[3]["value"] == 0
        assert data[4]["value"] == 0
        assert data[5]["value"] == 0
        assert data[6]["value"] == 0
        assert data[7]["value"] == 3

    def test_time_chart_without_dates_but_with_votes(
        self, conversation_with_votes, logged_client
    ):
        conversation = conversation_with_votes
        url = reverse(
            "boards:dataviz-votes_over_time", kwargs=conversation.get_url_kwargs()
        )
        response = logged_client.get(url)
        data = json.loads(response.content)

        assert data["start_date"] == conversation.votes.first().created.isoformat()
        assert data["end_date"] == conversation.votes.last().created.isoformat()

    def test_should_return_error_if_start_date_is_bigger_than_end_date(
        self, conversation, board, logged_client
    ):
        board.save()
        conversation.board = board
        conversation.save()

        url = reverse(
            "boards:dataviz-votes_over_time", kwargs=conversation.get_url_kwargs()
        )
        url = url + "?startDate=2021-10-13&endDate=2021-10-06"
        response = logged_client.get(url)
        assert json.loads(response.content) == {
            "error": "end date must be gratter then start date."
        }

    def test_time_chart_without_dates(self, conversation, board, logged_client):
        board.save()
        conversation.board = board
        conversation.save()

        base_url = reverse(
            "boards:dataviz-votes_over_time", kwargs=conversation.get_url_kwargs()
        )
        response = logged_client.get(base_url)
        assert json.loads(response.content) == {
            "data": [],
            "start_date": "",
            "end_date": "",
        }

    def test_board_owner_can_view_dataviz_dashboard(
        self, conversation, board, logged_client
    ):
        board.save()
        conversation.board = board
        conversation.save()

        clusterization = Clusterization.objects.create(
            conversation=conversation, cluster_status=ClusterStatus.ACTIVE
        )
        cluster = Cluster.objects.create(name="name", clusterization=clusterization)
        stereotype, _ = Stereotype.objects.get_or_create(
            name="name", owner=conversation.author
        )
        cluster.stereotypes.add(stereotype)

        url = reverse("boards:dataviz-dashboard", kwargs=conversation.get_url_kwargs())
        response = logged_client.get(url)
        assert (
            "Your conversation still does not have defined personas. Without personas, it is not possible to generate opinion groups."
            not in response.content.decode()
        )

    def test_get_page(self, conversation_with_comments, logged_client):
        conv = conversation_with_comments
        base_url = reverse("boards:dataviz-comments", kwargs=conv.get_url_kwargs())
        url = f"{base_url}?page=1"

        response = logged_client.get(url)
        comments = list(response.context_data["page"])
        assert conversation_with_comments.comments.all()[0].content == comments[0][1]
        assert conversation_with_comments.comments.all()[1].content == comments[1][1]
        assert conversation_with_comments.comments.all()[2].content == comments[2][1]
        assert conversation_with_comments.comments.all()[3].content == comments[3][1]

    def test_get_dashboard_with_clusters(
        self, cluster, stereotype_vote, comment, logged_client
    ):
        cluster.stereotypes.add(stereotype_vote.author)
        cluster.users.add(cluster.clusterization.conversation.author)
        cluster.save()
        conversation = cluster.conversation
        comment = conversation.create_comment(
            conversation.author, "aa", status="approved", check_limits=False
        )
        comment.vote(conversation.author, "agree")
        comment.save()
        url = reverse("boards:dataviz-dashboard", kwargs=conversation.get_url_kwargs())
        response = logged_client.get(url)
        assert response.status_code == 200
        assert response.context["biggest_cluster_data"].get("name") == "My Cluster"
        assert response.context["biggest_cluster_data"].get("content") == comment.content
        assert response.context["biggest_cluster_data"].get("percentage")

    def test_get_dashboard_without_clusters(
        self, cluster, stereotype_vote, logged_client
    ):
        cluster.stereotypes.add(stereotype_vote.author)
        cluster.users.add(cluster.clusterization.conversation.author)
        cluster.save()
        conversation = cluster.conversation
        dashboard_url = reverse(
            "boards:dataviz-dashboard", kwargs=conversation.get_url_kwargs()
        )
        response = logged_client.get(dashboard_url)
        assert response.status_code == 200
        assert response.context["biggest_cluster_data"] == {}


class TestCommentsReport(TestReportRoutes):
    def test_get_comments_dataframe(self, conversation_with_comments):
        comments_df = get_comments_dataframe(conversation_with_comments, "")
        assert comments_df.iloc[[0]].get("group").item() == ""
        assert comments_df.iloc[[1]].get("group").item() == ""
        assert comments_df.iloc[[2]].get("group").item() == ""
        assert comments_df.iloc[[3]].get("group").item() == ""
        assert len(comments_df.index) == 4

    def test_get_cluster_comments_dataframe(self, conversation_with_comments):
        clusterization = Clusterization.objects.create(
            conversation=conversation_with_comments, cluster_status=ClusterStatus.ACTIVE
        )
        cluster = Cluster.objects.create(name="name", clusterization=clusterization)

        clusters_filter = CommentsReportClustersFilter(
            cluster_ids=[cluster.id], conversation=conversation_with_comments
        )
        comments_df = clusters_filter.filter()

        assert comments_df.iloc[[0]].get("group").item() == cluster.name
        assert comments_df.iloc[[1]].get("group").item() == cluster.name
        assert comments_df.iloc[[2]].get("group").item() == cluster.name
        assert comments_df.iloc[[3]].get("group").item() == cluster.name
        assert len(comments_df.index) == 4

    def test_filter_comments_by_group(self, conversation_with_comments):
        clusterization = Clusterization.objects.create(
            conversation=conversation_with_comments, cluster_status=ClusterStatus.ACTIVE
        )
        clusters_filter = CommentsReportClustersFilter(
            cluster_ids=[], conversation=conversation_with_comments
        )
        filtered_comments_df = clusters_filter.filter()
        assert filtered_comments_df.iloc[[0]].get("group").item() == ""
        assert filtered_comments_df.iloc[[1]].get("group").item() == ""
        assert filtered_comments_df.iloc[[2]].get("group").item() == ""
        assert filtered_comments_df.iloc[[3]].get("group").item() == ""
        assert len(filtered_comments_df.index) == 4

        cluster = Cluster.objects.create(name="name", clusterization=clusterization)
        clusters_filter = CommentsReportClustersFilter(
            cluster_ids=[cluster.id], conversation=conversation_with_comments
        )
        filtered_comments_df = clusters_filter.filter()
        assert filtered_comments_df.iloc[[0]].get("group").item() == cluster.name
        assert filtered_comments_df.iloc[[1]].get("group").item() == cluster.name
        assert filtered_comments_df.iloc[[2]].get("group").item() == cluster.name
        assert filtered_comments_df.iloc[[3]].get("group").item() == cluster.name
        assert len(filtered_comments_df.index) == 4

    def test_sort_comments_dataframe_in_descending_order(
        self, conversation_with_comments
    ):
        clusters_filter = CommentsReportClustersFilter(
            cluster_ids=[], conversation=conversation_with_comments
        )
        comments_df = clusters_filter.filter()

        orderby_filter = ReportOrderByFilter("agree", comments_df)
        sorted_comments_df = orderby_filter.filter()
        assert sorted_comments_df.iloc[[0]].get("content").item() == "aa"
        assert round(sorted_comments_df.iloc[[0]].get("agree").item(), 1) == 100.0
        assert sorted_comments_df.iloc[[1]].get("content").item() == "aaa"
        assert round(sorted_comments_df.iloc[[1]].get("agree").item(), 1) == 66.7
        assert sorted_comments_df.iloc[[2]].get("content").item() == "aaaa"
        assert round(sorted_comments_df.iloc[[2]].get("agree").item(), 1) == 33.3
        assert sorted_comments_df.iloc[[3]].get("content").item() == "test"
        assert round(sorted_comments_df.iloc[[3]].get("agree").item(), 1) == 0.0

        orderby_filter = ReportOrderByFilter("disagree", comments_df)
        sorted_comments_df = orderby_filter.filter()
        assert sorted_comments_df.iloc[[0]].get("content").item() == "test"
        assert round(sorted_comments_df.iloc[[0]].get("disagree").item(), 1) == 100.0
        assert sorted_comments_df.iloc[[1]].get("content").item() == "aaaa"
        assert round(sorted_comments_df.iloc[[1]].get("disagree").item(), 1) == 66.7
        assert sorted_comments_df.iloc[[2]].get("content").item() == "aaa"
        assert round(sorted_comments_df.iloc[[2]].get("disagree").item(), 1) == 33.3
        assert sorted_comments_df.iloc[[3]].get("content").item() == "aa"
        assert round(sorted_comments_df.iloc[[3]].get("disagree").item(), 1) == 0.0

    def test_sort_comments_dataframe_in_ascending_order(self, conversation_with_comments):
        clusters_filter = CommentsReportClustersFilter(
            cluster_ids=[], conversation=conversation_with_comments
        )
        comments_df = clusters_filter.filter()

        orderby_filter = ReportOrderByFilter("agree", comments_df, True)
        sorted_comments_df = orderby_filter.filter()
        assert sorted_comments_df.iloc[[0]].get("content").item() == "test"
        assert round(sorted_comments_df.iloc[[0]].get("agree").item(), 1) == 0.0
        assert sorted_comments_df.iloc[[1]].get("content").item() == "aaaa"
        assert round(sorted_comments_df.iloc[[1]].get("agree").item(), 1) == 33.3
        assert sorted_comments_df.iloc[[2]].get("content").item() == "aaa"
        assert round(sorted_comments_df.iloc[[2]].get("agree").item(), 1) == 66.7
        assert sorted_comments_df.iloc[[3]].get("content").item() == "aa"
        assert round(sorted_comments_df.iloc[[3]].get("agree").item(), 1) == 100.0

        orderby_filter = ReportOrderByFilter("disagree", comments_df, True)
        sorted_comments_df = orderby_filter.filter()
        assert sorted_comments_df.iloc[[0]].get("content").item() == "aa"
        assert round(sorted_comments_df.iloc[[0]].get("disagree").item(), 1) == 0.0
        assert sorted_comments_df.iloc[[1]].get("content").item() == "aaa"
        assert round(sorted_comments_df.iloc[[1]].get("disagree").item(), 1) == 33.3
        assert sorted_comments_df.iloc[[2]].get("content").item() == "aaaa"
        assert round(sorted_comments_df.iloc[[2]].get("disagree").item(), 1) == 66.7
        assert sorted_comments_df.iloc[[3]].get("content").item() == "test"
        assert round(sorted_comments_df.iloc[[3]].get("disagree").item(), 1) == 100.0

    def test_search_string_comments_dataframe(self, conversation_with_comments):
        clusters_filter = CommentsReportClustersFilter(
            cluster_ids=[], conversation=conversation_with_comments
        )
        comments_df = clusters_filter.filter()

        search_filter = CommentsReportSearchFilter("aa", comments_df)
        filtered_comments_df = search_filter.filter()
        assert len(filtered_comments_df.index) == 3
        search_filter = CommentsReportSearchFilter("aaa", comments_df)
        filtered_comments_df = search_filter.filter()
        assert len(filtered_comments_df.index) == 2
        search_filter = CommentsReportSearchFilter("t", comments_df)
        filtered_comments_df = search_filter.filter()
        assert len(filtered_comments_df.index) == 1

    def test_get_modal(self, conversation_with_comments, logged_client):
        comments = conversation_with_comments.comments.all()
        index = 0
        comment = comments[index]
        base_url = reverse("dataviz:comments-modal", kwargs={"pk": comment.id})
        url = f"{base_url}?comments={comment.id}&comments={comments[1].id}"
        comments_ids = list(comments.values_list("id", flat=True))
        value = 100
        comments_ids_dict = [
            {
                "comment": id,
                "agree": value,
                "disagree": 0,
                "skipped": 0,
                "convergence": value,
                "participation": value,
                "group": "",
            }
            for id in comments_ids
        ]

        response = logged_client.post(
            url, {"comments": json.dumps(comments_ids_dict), "current_index": index}
        )
        context = response.context
        comment_statistics = context["comment_statistics"]
        statistics = comment.statistics(ratios=True)
        assert context["comment"] == comment
        assert context["next_id"] == comment.next(index, comments_ids_dict)
        assert context["previous_id"] == comment.previous(index, comments_ids_dict)
        assert comment_statistics["agree"] == statistics["agree_ratio"] * 100
        assert comment_statistics["disagree"] == statistics["disagree_ratio"] * 100
        assert comment_statistics["skipped"] == statistics["skip_ratio"] * 100
        assert context["comment"].n_votes == statistics["total"]


class TestUsersReport(TestReportRoutes):
    no_group_text = gettext("No group")

    @pytest.fixture
    def user_cluster(self, conversation_with_comments):
        clusterization = Clusterization.objects.create(
            conversation=conversation_with_comments, cluster_status=ClusterStatus.ACTIVE
        )
        cluster = Cluster.objects.create(name="name", clusterization=clusterization)
        comments = conversation_with_comments.comments
        stereotype, _ = Stereotype.objects.get_or_create(
            name="name", owner=conversation_with_comments.author
        )
        cluster.stereotypes.add(stereotype)

        StereotypeVote.objects.create(
            choice=Choice.AGREE, comment=comments[0], author_id=stereotype.id
        )
        StereotypeVote.objects.create(
            choice=Choice.SKIP, comment=comments[1], author_id=stereotype.id
        )
        StereotypeVote.objects.create(
            choice=Choice.DISAGREE, comment=comments[2], author_id=stereotype.id
        )
        StereotypeVote.objects.create(
            choice=Choice.DISAGREE, comment=comments[3], author_id=stereotype.id
        )
        clusterization.update_clusterization(force=True)
        yield cluster

    def test_get_user_dataframe(self, conversation_with_comments):
        users_df = get_user_dataframe(conversation_with_comments, "")
        assert users_df.iloc[[0]].get("group").item() == TestUsersReport.no_group_text
        assert users_df.iloc[[1]].get("group").item() == TestUsersReport.no_group_text
        assert users_df.iloc[[2]].get("group").item() == TestUsersReport.no_group_text
        assert len(users_df.index) == 3

    def test_get_cluster_users_dataframe(self, conversation_with_comments, user_cluster):
        clusters_filter = UsersReportClustersFilter(
            [user_cluster.id], conversation_with_comments
        )
        users_df = clusters_filter.filter()

        assert users_df.iloc[[0]].get("group").item() == user_cluster.name
        assert users_df.iloc[[1]].get("group").item() == user_cluster.name
        assert users_df.iloc[[2]].get("group").item() == user_cluster.name
        assert len(users_df.index) == 3

    def test_filter_users_by_group_with_no_group(self, conversation_with_comments):
        clusters_filter = UsersReportClustersFilter([], conversation_with_comments)
        filtered_users_df = clusters_filter.filter()
        assert (
            filtered_users_df.iloc[[0]].get("group").item()
            == TestUsersReport.no_group_text
        )
        assert (
            filtered_users_df.iloc[[1]].get("group").item()
            == TestUsersReport.no_group_text
        )
        assert (
            filtered_users_df.iloc[[2]].get("group").item()
            == TestUsersReport.no_group_text
        )
        assert len(filtered_users_df.index) == 3

    def test_filter_users_by_group(self, conversation_with_comments, user_cluster):
        clusters_filter = UsersReportClustersFilter(
            [user_cluster.id], conversation_with_comments
        )
        filtered_users_df = clusters_filter.filter()
        assert filtered_users_df.iloc[[0]].get("group").item() == user_cluster.name
        assert filtered_users_df.iloc[[1]].get("group").item() == user_cluster.name
        assert filtered_users_df.iloc[[2]].get("group").item() == user_cluster.name
        assert len(filtered_users_df.index) == 3

    def test_sort_user_dataframe_in_descending_order(self, conversation_with_comments):
        clusters_filter = UsersReportClustersFilter([], conversation_with_comments)
        users_df = clusters_filter.filter()

        orderby_filter = ReportOrderByFilter("email", users_df)
        sorted_users_df = orderby_filter.filter()
        assert sorted_users_df.iloc[[0]].get("email").item() == "user3@email.br"
        assert sorted_users_df.iloc[[1]].get("email").item() == "user2@email.br"
        assert sorted_users_df.iloc[[2]].get("email").item() == "user1@email.br"

        orderby_filter = ReportOrderByFilter("name", users_df)
        sorted_users_df = orderby_filter.filter()
        assert sorted_users_df.iloc[[0]].get("email").item() == "user3@email.br"
        assert sorted_users_df.iloc[[1]].get("email").item() == "user2@email.br"
        assert sorted_users_df.iloc[[2]].get("email").item() == "user1@email.br"

        orderby_filter = ReportOrderByFilter("date_joined", users_df)
        sorted_users_df = orderby_filter.filter()
        assert sorted_users_df.iloc[[0]].get("email").item() == "user3@email.br"
        assert sorted_users_df.iloc[[1]].get("email").item() == "user2@email.br"
        assert sorted_users_df.iloc[[2]].get("email").item() == "user1@email.br"

    def test_sort_users_dataframe_in_ascending_order(self, conversation_with_comments):
        clusters_filter = UsersReportClustersFilter([], conversation_with_comments)
        users_df = clusters_filter.filter()

        orderby_filter = ReportOrderByFilter("email", users_df, True)
        sorted_users_df = orderby_filter.filter()
        assert sorted_users_df.iloc[[0]].get("email").item() == "user1@email.br"
        assert sorted_users_df.iloc[[1]].get("email").item() == "user2@email.br"
        assert sorted_users_df.iloc[[2]].get("email").item() == "user3@email.br"

        orderby_filter = ReportOrderByFilter("date_joined", users_df, True)
        sorted_users_df = orderby_filter.filter()
        assert sorted_users_df.iloc[[0]].get("email").item() == "user1@email.br"
        assert sorted_users_df.iloc[[1]].get("email").item() == "user2@email.br"
        assert sorted_users_df.iloc[[2]].get("email").item() == "user3@email.br"

    def test_search_string_users_dataframe(self, conversation_with_comments):
        clusters_filter = UsersReportClustersFilter([], conversation_with_comments)
        users_df = clusters_filter.filter()

        search_filter = UsersReportSearchFilter("user", users_df)
        filtered_users_df = search_filter.filter()
        assert len(filtered_users_df.index) == 3
        search_filter = UsersReportSearchFilter("user1", users_df)
        filtered_users_df = search_filter.filter()
        assert len(filtered_users_df.index) == 1
        search_filter = UsersReportSearchFilter("user2", users_df)
        filtered_users_df = search_filter.filter()
        assert len(filtered_users_df.index) == 1

        search_filter = UsersReportSearchFilter("@email.br", users_df)
        filtered_users_df = search_filter.filter()
        assert len(filtered_users_df.index) == 3
