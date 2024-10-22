from logging import getLogger

from boogie.models import QuerySet, F, Manager, Value, IntegerField
from sidekick import import_later
from django.contrib.auth import get_user_model

from ej_conversations.math import imputation
from ej_conversations.models import Conversation, Comment
from ..mixins import ClusterizationBaseMixin

pd = import_later("pandas")
np = import_later("numpy")
impute = import_later("sklearn.impute")
clusterization_pipeline = import_later(
    "..math:clusterization_pipeline", package=__package__
)
models = import_later(".models", package=__package__)
log = getLogger("ej")


class ClusterQuerySet(ClusterizationBaseMixin, QuerySet):
    """
    Represents a table of Cluster objects.
    """

    def get_clusters(self):
        return self

    def users(self, by_comment=False):
        """
        Queryset of users explicitly clusterized in the current cluster set.
        """
        if by_comment:
            return super().users(by_comment)
        return get_user_model().objects.filter(clusters__in=self)

    def participants(self):
        """
        Queryset with all participants of the conversations associated
        with the current cluster set.
        """
        return super().users()

    def check_unique_clusterization(self):
        """
        Raise ValueError if cluster set does *NOT* belong to a single
        clusterization.
        """
        # Fast-track without touching the database if this is a related
        # query from a Clusterization object.
        related = self._known_related_objects
        if len(related) == 1:
            # noinspection PyProtectedMember
            data = related.get(self.model._meta.get_field("clusterization"))
            if data is not None and len(data) == 1:
                return

        # Otherwise we check in the database if we can find more than one
        # clusterization root
        if self.values_list("clusterization").distinct().count() > 1:
            msg = "more than one clusterization found on cluster dataset"
            raise ValueError(msg)

    def conversations(self):
        return Conversation.objects.filter(clusterization__clusters__in=self)

    def votes_data(self, conversation=None):
        """
        Return a query set of (cluster, comment, choice) items from the given
        conversation.
        """
        return conversation.votes.values_list(
            "comment__conversation_id", "comment_id", "choice"
        )

    def votes_dataframe(self, conversation):
        """
        Like .votes_data(), but Return a dataframe.
        """
        data = list(self.votes_data(conversation))
        return pd.DataFrame(data, columns=["cluster, comment", "choice"])

    def votes_table(
        self,
        data_imputation=None,
        cluster_col="cluster",
        kind_col=None,
        mean_stereotype=False,
        non_classified=False,
        check_unique=True,
        **kwargs,
    ):
        """
        Return a votes table that joins the results from regular users
        and stereotypes. Stereotypes are identified with negative index labels.

        It accepts the same methods as votes_table() function.

        Args:
            data_imputation ({'mean', None}):
                Data imputation method for filling missing values.
            mean_stereotype (bool):
                If True, uses the average stereotype vote at each cluster as
                the stereotype rows. If this is set, stereotypes are
                identified by the cluster index instead of the stereotype index.
            non_classified (bool):
                If True, include users that were not clusterized in the current
                cluster set. Otherwise only return users explicitly present on
                the current clusters.
            check_unique (bool):
                Raises a ValueError if clusters do not have a common
                root (default). If set to False, skip this test. NOTE: if cluster
                set has more than one root, users can be on multiple clusters,
                which can lead to non-determinism on the cluster label assigned
                to user.
            cluster_col (str, None):
                Name of the column that identifies the cluster of each
                user/stereotype. Set to None to disable it.
            kind_col (str, None):
                If True, instead of using negative indexes to differentiate
                users from stereotypes, it adds an extra column with the given
                name with a boolean which is True when then entry is an user
                and False otherwise.
        """

        # Select comments
        if "comments" in kwargs:
            raise TypeError("invalid argument: comments")
        kwargs["comments"] = self.comments()

        # Checks
        if check_unique:
            self.check_unique_clusterization()

        # Fetch votes from database
        kwargs.update(kind_col=kind_col, cluster_col=cluster_col)
        stereotype_votes = self._stereotypes_votes_table(mean_stereotype, **kwargs)
        user_votes = self._users_votes_table(non_classified, **kwargs)

        # Imputation must occur after both set of votes are joined together.
        votes = user_votes.append(stereotype_votes)
        if cluster_col is None:
            return imputation(votes, data_imputation)

        cluster_series = votes[cluster_col]
        votes = imputation(votes, data_imputation)
        votes[cluster_col] = cluster_series
        return votes.dropna()

    def _stereotypes_votes_table(self, mean, kind_col, cluster_col, **kwargs):
        # Prepare stereotype votes
        if mean:
            stereotype_votes = self.mean_stereotypes_votes_table()
        else:
            stereotypes = self.stereotypes()
            stereotype_votes = stereotypes.votes_table(**kwargs)

        if kind_col:
            stereotype_votes[kind_col] = False
        elif len(stereotype_votes.index) != 0:
            stereotype_votes.index *= -1

        if cluster_col is not None:
            if self.count():
                clusters = self._get_cluster_to_user_column_table("stereotypes")
                if not kind_col and len(clusters.index) != 0:
                    clusters.index *= -1
            else:
                clusters = float("nan")
            stereotype_votes[cluster_col] = clusters
        return stereotype_votes

    def _users_votes_table(self, non_classified, kind_col, cluster_col, **kwargs):
        users = self.participants() if non_classified else self.users()
        user_votes = users.votes_table(**kwargs)

        if kind_col is not None:
            user_votes[kind_col] = True

        if cluster_col is not None:
            if self.count():
                clusters = self._get_cluster_to_user_column_table("users")
            else:
                clusters = float("nan")
            user_votes[cluster_col] = clusters
        return user_votes

    def _get_cluster_to_user_column_table(self, user_field="users"):
        int_field = IntegerField()

        cluster, *rest = self
        users = list(
            getattr(cluster, user_field)
            .annotate(cluster=Value(cluster.id, output_field=int_field))
            .values_list("id", "cluster")
        )

        for cl in rest:
            users.extend(
                getattr(cl, user_field)
                .annotate(cluster=Value(cl.id, output_field=int_field))
                .values_list("id", "cluster")
            )

        # Remove duplicates from cluster/user pairs
        # This should never happen, but sometimes it does and we don't want to
        # crash the application due to a minor bug.
        data = list(dict(users).items())
        col = pd.DataFrame(data, columns=["user", "cluster"])
        col.index = col.pop("user")
        col.index.name = "author"
        return col.pop("cluster")

    def find_clusters(self, pipeline_factory=None, commit=True):
        """
        Find clusters using the given clusterization pipeline and write results
        on the database.

        Args:
            pipeline_factory:
                A function from the number of clusters to Clusterization
                pipeline. The pipeline should receive a dataframe with raw
                voting mean_votes, impute values to missing mean_votes, normalize and
                classify using stereotype mean_votes. Unless you know what you are
                doing it must be constructed with
                :func:`ej_clusters.math.clusterization_pipeline`.
            commit (bool):
                If False, prevents it from updating the database.

        Returns:
            A pair with a mapping from clusters ids to the corresponding sequence
            of user ids. The mapping has a .pipeline attribute that holds the
            resulting clusterization pipeline.
        """

        cluster_ids = list(self.values_list("id", flat=True))
        n_clusters = len(cluster_ids)

        # Check the number of clusters to initialize the pipeline
        pipeline_factory = pipeline_factory or clusterization_pipeline()
        pipeline = pipeline_factory(n_clusters)
        if n_clusters == 0:
            log.error("Trying to clusterize empty cluster set.")
            return ClusterDict(pipeline=pipeline)
        elif n_clusters == 1:
            log.warning("Creating clusters for cluster set with a single element.")

        # Collect votes
        imputer = impute.SimpleImputer()
        votes_qs = self.votes().filter(comment__status=Comment.STATUS.approved)
        user_votes = votes_qs.votes_table()
        if not user_votes.empty:
            user_votes.values[:] = imputer.fit_transform(user_votes)
            cluster_votes = self._cluster_votes(cluster_ids, votes_qs)

            # Aggregate user and cluster votes
            cluster_votes = pd.DataFrame(cluster_votes)
            cluster_votes.index *= -1
            votes = user_votes.append(cluster_votes)
            votes_data = imputer.transform(votes.values)

            # Find labels and associate them with cluster labels
            labels = [cluster_ids[i] for i in pipeline.fit_predict(votes_data)]
            user_labels = labels[:-n_clusters]
            user_labels = pd.DataFrame(
                [list(user_votes.index), user_labels], index=["user", "label"]
            ).T
            stereotype_labels = labels[len(user_labels) :]

            return self._save_clusterization(
                pipeline, cluster_ids, stereotype_labels, user_labels, commit
            )

    def _cluster_votes(self, cluster_ids, votes):
        comments = Comment.objects.filter(
            id__in=votes.values_list("comment_id", flat=True)
        )
        stereotype_votes = self.stereotype_votes(comments).votes_table("zero")
        stereotype_ids = self.dataframe("id", "stereotypes__id", index=None)

        stereotype_with_votes = list(
            set(self.stereotype_votes(comments).values_list("author__id", flat=True))
        )
        stereotype_ids = stereotype_ids[
            stereotype_ids["stereotypes__id"].isin(stereotype_with_votes)
        ]

        cluster_votes = []
        for cluster_id in cluster_ids:
            ids = stereotype_ids[stereotype_ids.id == cluster_id]["stereotypes__id"]
            mean_votes = stereotype_votes.loc[ids].mean(0)

            # We fill empty clusters with random values to avoid superposition of
            # clusters
            if (mean_votes == 0).all():
                clusterization = self.get(id=cluster_id).clusterization
                log.warning(
                    f"[clusters] cluster {cluster_id} of {clusterization} is empty!"
                )
                mean_votes.values[:] = np.random.uniform(-1, 1, size=len(mean_votes))

            mean_votes.name = cluster_id
            cluster_votes.append(mean_votes)
        return cluster_votes

    def _save_clusterization(self, pipeline, cluster_ids, stereotype, user, commit=True):
        result = ClusterDict(pipeline=pipeline)
        m2m_objects = []
        m2m = self.model.users.through
        for expected_id, got_id in zip(cluster_ids, stereotype):
            if expected_id != got_id:
                expected = self.get(id=expected_id)
                got = self.get(id=got_id)
                log.warning(
                    f"[clusters] Inconsistent clusters ({expected.clusterization}): "
                    f'stereotype for "{expected.name}" was classified as "{got.name}"!'
                )

            user_ids = user[user.label == expected_id].user.values
            result[expected_id] = user_ids
            if commit:
                m2m_objects.extend(
                    m2m(cluster_id=expected_id, user_id=uid) for uid in user_ids
                )

        if commit:
            m2m.objects.filter(cluster__in=cluster_ids).delete()
            m2m.objects.bulk_create(m2m_objects)
        return result

    def mean_stereotypes_votes_table(self, data_imputation=None):
        """
        Return a dataframe with the average vote per cluster considering all
        stereotypes in the cluster.
        """
        votes = (
            self.stereotype_votes()
            .annotate(cluster=F.author.clusters)
            .dataframe("author", "comment", "choice", "cluster")
        )

        if votes.shape[0]:
            votes = votes.pivot_table(
                values="choice", index=["author", "cluster"], columns="comment"
            )
        else:
            raise ValueError("no votes found")

        votes["cluster"] = votes.index.get_level_values("cluster")
        votes.index = np.arange(votes.shape[0])
        votes = votes.groupby("cluster").mean()
        return imputation(votes, data_imputation)


class ClusterManager(Manager.from_queryset(ClusterQuerySet)):
    """
    Manage creation and query of cluster objects.
    """

    def create_with_stereotypes(self, name, stereotypes=None, comments=None):
        """
        Creates a new cluster with the given stereotypes.

        If no stereotype is given, creates a single stereotype with the same
        name as the cluster.
        """
        raise NotImplementedError


class ClusterDict(dict):
    """
    Custom dict class that stores extra attributes.
    """

    def __init__(self, d=(), pipeline=None):
        super().__init__(d)
        self.pipeline = pipeline
