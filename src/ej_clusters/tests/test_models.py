import pytest
from ej_clusters.mommy_recipes import ClusterRecipes
from ej_conversations.tests.test_views import ConversationSetup


class TestClusterization(ClusterRecipes):
    def test_inject_clusters_related_manager_on_conversation(
        self, conversation_db
    ):
        conversation_db.get_clusterization()
        assert hasattr(conversation_db.clusterization, "clusters")
        assert hasattr(conversation_db, "clusters")

    def test_clusterization_str_method(self, conversation_db):
        conversation_db.get_clusterization()
        clusterization = conversation_db.clusterization

        assert str(clusterization) == f"{conversation_db} (0 clusters)"
        assert (
            f"{clusterization.get_absolute_url()}"
            == f"{conversation_db.get_absolute_url()}stereotypes/"
        )


class TestCluster(ConversationSetup):
    @pytest.fixture
    def conversation_without_votes(self, conversation, base_board, base_user):
        conversation.author = base_user
        base_board.owner = base_user
        base_board.save()
        conversation.board = base_board
        conversation.save()

        conversation.create_comment(
            base_user, "aa", status="approved", check_limits=False
        )

        conversation.create_comment(
            base_user, "aaa", status="approved", check_limits=False
        )
        conversation.create_comment(
            base_user, "aaaa", status="approved", check_limits=False
        )
        conversation.save()
        return conversation

    def test_concat_statistics_to_dataframe(
        self, clusterization, cluster, vote
    ):
        clusterization.update_clusterization(force=True)
        cluster_df = cluster.concat_statistics_to_dataframe()
        assert cluster_df.iloc[0]["group"] == cluster.name
        assert cluster_df["content"].any()
        assert cluster_df["author"].any()
        assert cluster_df["participation"].any()
        assert cluster_df["convergence"].any()
        assert cluster_df["agree"].any()
        assert cluster_df.iloc[0]["disagree"] == 0.0
        assert cluster_df.iloc[0]["skipped"] == 0.0

    def test_clusterization_without_votes(self, conversation_without_votes):
        clusterization = conversation_without_votes.get_clusterization()
        clusterization.update_clusterization(force=True)
        assert clusterization.stereotype_votes.count() == 0
