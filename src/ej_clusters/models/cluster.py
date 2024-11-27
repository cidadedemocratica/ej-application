from boogie import models
from django.contrib.auth import get_user_model
from django.db.models import Subquery
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from model_utils.models import TimeStampedModel
from sidekick import delegate_to, lazy, import_later, placeholder as this

from ej_conversations.models import Comment
from .cluster_queryset import ClusterManager
from .stereotype_vote import StereotypeVote

pd = import_later("pandas")
np = import_later("numpy")
clusterization_pipeline = import_later(
    "..math:clusterization_pipeline", package=__package__
)


class Cluster(TimeStampedModel):
    """
    Represents an opinion group.
    """

    clusterization = models.ForeignKey(
        "Clusterization", on_delete=models.CASCADE, related_name="clusters"
    )
    name = models.CharField(_("Name"), max_length=64)
    description = models.TextField(
        _("Description"), blank=True, help_text=_("How was this cluster conceived?")
    )
    users = models.ManyToManyField(get_user_model(), related_name="clusters", blank=True)
    stereotypes = models.ManyToManyField("Stereotype", related_name="clusters")
    conversation = delegate_to("clusterization")
    comments = delegate_to("clusterization")
    objects = ClusterManager()

    @property
    def votes(self):
        return self.clusterization.votes.filter(author__in=self.users.all())

    @property
    def stereotype_votes(self):
        return self.clusterization.stereotype_votes.filter(
            author__in=self.stereotypes.all()
        )

    n_votes = lazy(this.votes.count())
    n_users = lazy(this.users.count())
    n_stereotypes = lazy(this.stereotypes.count())
    n_stereotype_votes = lazy(this.n_stereotype_votes.count())

    def __str__(self):
        msg = _('{name} ("{conversation}" conversation, {n} users)')
        return msg.format(
            name=self.name, conversation=self.conversation, n=self.users.count()
        )

    def get_absolute_url(self):
        args = {
            "conversation": self.conversation,
            "cluster": self,
            "board_slug": self.conversation.board.slug,
        }
        return reverse("boards:cluster-detail", kwargs=args)

    def mean_stereotype(self):
        """
        Return the mean stereotype for cluster.
        """
        stereotypes = self.stereotypes.all()
        votes = StereotypeVote.objects.filter(
            author__in=Subquery(stereotypes.values("id"))
        ).values_list("comment", "choice")
        df = pd.DataFrame(list(votes), columns=["comment", "choice"])
        if len(df) == 0:
            return pd.DataFrame([], columns=["choice"])
        else:
            return df.pivot_table("choice", index="comment", aggfunc="mean")

    def comments_statistics_summary_dataframe(self, normalization=1.0):
        """
        Like comments.statistics_summary_dataframe(), but restricts votes to
        users in the current clusters.
        """
        kwargs = dict(normalization=normalization, votes=self.votes)
        return self.comments.statistics_summary_dataframe(**kwargs)

    def separate_comments(self, sort=True):
        """
        Separate comments into a pair for comments that cluster agrees to and
        comments that cluster disagree.

        By default, only comments with participation statistic higher than 30% are returned.
        """
        tol = 1e-6
        table = self.votes.votes_table()

        n_agree = (table > 0).sum()
        n_disagree = (table < 0).sum()
        total = n_agree + n_disagree + (table == 0).sum() + tol

        d_agree = dict(((n_agree[n_agree >= n_disagree] + tol) / total).dropna().items())
        d_disagree = dict(
            ((n_disagree[n_disagree > n_agree] + tol) / total).dropna().items()
        )

        agree = []
        disagree = []

        comments_df = self.comments_statistics_summary_dataframe()
        for comment in Comment.objects.filter(id__in=d_agree):
            # It would accept 0% agreement since we test sfor n_agree >= n_disagree
            # We must prevent cases with 0 agrees (>= 0 disagrees) to enter in
            # the calculation
            n_agree = d_agree[comment.id]
            comment.agree = n_agree
            comment.participation = comments_df.loc[comment.id]["participation"]
            agree.append(comment)

        for comment in Comment.objects.filter(id__in=d_disagree):
            comment.disagree = d_disagree[comment.id]
            comment.participation = comments_df.loc[comment.id]["participation"]
            disagree.append(comment)

        if sort:
            agree.sort(key=lambda c: c.agree, reverse=True)
            disagree.sort(key=lambda c: c.disagree, reverse=True)

        return agree, disagree

    def concat_statistics_to_dataframe(self, df: pd.DataFrame = pd.DataFrame()):
        """
        concat_results_to_dataframe adds cluster voting results to df argument.
        Useful for exporting comments raw data.
        """
        cluster_df = self.comments.statistics_summary_dataframe(votes=self.votes)
        if not cluster_df.empty:
            cluster_df["group"] = self.name
            df = pd.concat([df, cluster_df])
            df.sort_values(by=["content", "created"], inplace=True)
        return df
