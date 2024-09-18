from dataclasses import dataclass

import pandas as pd

from ej_conversations.models import Conversation
from ej_dataviz.utils import (
    add_group_column,
    get_cluster_or_404,
    get_clusters,
    get_comments_dataframe,
    get_user_dataframe,
)


@dataclass
class CommentsDataframeUtils:
    comments_df: pd.DataFrame

    def search_content(self, text):
        """
        Filter the comments dataframe by the content column. It will be checked if the
        content has the substring variable.
        """

        return self.comments_df[self.comments_df.content.str.contains(text, case=False)]

    def get_cluster_comments_df(self, cluster, cluster_name):
        """
        Gets the cluster comments dataframe from comments_statistics_summary_dataframe
        and sets the group column for each comment row.
        """
        df = cluster.comments_statistics_summary_dataframe(normalization=100)
        add_group_column(df, cluster_name)
        return df

    def filter_by_cluster(self, clusters, cluster_filters):
        """
        Gets the conversation comments (comments_df) and cluster comments
        filtered by the group specified in cluster_filters.
        """
        for cluster in clusters:
            if cluster.name in cluster_filters:
                cluster_comments_df = self.get_cluster_comments_df(cluster, cluster.name)
                self.comments_df = self.comments_df.append(cluster_comments_df)

        if "general" not in cluster_filters:
            self.comments_df = self.comments_df[self.comments_df.group != ""]

        return self.comments_df


@dataclass
class UsersDataframeUtils:
    users_df: pd.DataFrame

    def search_user(self, text):
        """
        Filter users dataframe by the name or email column. It will be checked if the
        user has the substring variable.
        """
        search_by_name = self.users_df.name.str.contains(text, case=False)
        search_by_email = self.users_df.email.str.contains(text, case=False)
        return self.users_df[search_by_name | search_by_email]

    def filter_by_cluster(self, clusters, cluster_filters):
        """
        Gets the conversation participants (users_df) and cluster users
        filtered by the group specified in cluster_filters.
        """
        return self.users_df[self.users_df["group"].isin(cluster_filters)]


class ReportClustersFilter:
    def __init__(self, cluster_ids: list, conversation: Conversation):
        self.cluster_ids = cluster_ids
        self.conversation = conversation
        self.clusters_filters = []

    def filter(self):
        """
        Returns a dataframe with the conversation statistics, filtered by cluster_ids.
        """

        df = self.get_dataframe(self.conversation)
        if not self.cluster_ids:
            return df
        for cluster_id in self.cluster_ids:
            try:
                cluster = get_cluster_or_404(cluster_id, self.conversation)
                self.clusters_filters.append(cluster.name)
            except Exception:
                pass
        dataframe_utils = self.get_dataframe_utils(df)
        clusters = get_clusters(self.conversation)

        return dataframe_utils.filter_by_cluster(clusters, self.clusters_filters)

    def get_dataframe(self, conversation: Conversation, cluster_name: str = ""):
        pass

    def get_dataframe_utils(self, df):
        pass


class CommentsReportClustersFilter(ReportClustersFilter):
    """
    Implements get_dataframe method to return a dataframe with comments statistics.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get_dataframe(self, conversation: Conversation, cluster_name: str = ""):
        return get_comments_dataframe(conversation, cluster_name)

    def get_dataframe_utils(self, df):
        return CommentsDataframeUtils(df)


class UsersReportClustersFilter(ReportClustersFilter):
    """
    Implements get_dataframe method to return a dataframe with participants statistics.
    """

    def get_dataframe(self, conversation: Conversation, page_number: int = 1):
        return get_user_dataframe(conversation, page_number)

    def get_dataframe_utils(self, df):
        return UsersDataframeUtils(df)


class CommentsReportSearchFilter:
    def __init__(self, text: str, comments_df: pd.DataFrame):
        self.text = text
        self.comments_df = comments_df

    def filter(self):
        commentsDataframeUtils = CommentsDataframeUtils(self.comments_df)
        if self.text:
            return commentsDataframeUtils.search_content(self.text)
        return self.comments_df


class UsersReportSearchFilter:
    def __init__(self, text: str, users_df: pd.DataFrame):
        self.text = text
        self.users_df = users_df

    def filter(self):
        usersDataframeUtils = UsersDataframeUtils(self.users_df)
        if self.text:
            return usersDataframeUtils.search_user(self.text)
        return self.users_df


class ReportOrderByFilter:
    """
    Implements filter method to return a dataframe ordered by some column.
    """

    def __init__(
        self,
        order,
        report_df: pd.DataFrame,
        ascending=False,
        default_order: str = "comment",
    ):
        self.order = order
        self.report_df = report_df
        self.ascending = ascending
        self.default_order = default_order

    def filter(self):
        """
        Returns a dataframe ordered by some column.
        """
        if not self.order or self.order == "created":
            return self.report_df.sort_values(
                self.default_order, ascending=self.ascending
            )
        return self.report_df.sort_values(self.order, ascending=self.ascending)
