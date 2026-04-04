from model_mommy.recipe import Recipe, foreign_key as _foreign_key
from sidekick import record

from ej_conversations.enums import Choice
from ej_conversations.mommy_recipes import ConversationRecipes
from .models import Stereotype, StereotypeVote, Clusterization, Cluster

__all__ = ["ClusterRecipes"]


class ClusterRecipes(ConversationRecipes):
    clusterization = Recipe(
        Clusterization,
        conversation=_foreign_key(ConversationRecipes.conversation),
    )
    cluster = Recipe(
        Cluster, clusterization=_foreign_key(clusterization), name="cluster"
    )
    stereotype = Recipe(
        Stereotype,
        name="stereotype",
        owner=_foreign_key(
            ConversationRecipes.author.extend(
                email="stereotype-author@domain.com"
            )
        ),
    )
    stereotype_vote = Recipe(
        StereotypeVote,
        author=stereotype.make,
        choice=Choice.AGREE,
        comment=_foreign_key(ConversationRecipes.comment),
    )

    def get_data(self, request):
        data = super().get_data(request)
        stereotype = self.stereotype.make(owner=data.author)
        votes = [
            self.stereotype_vote.make(author=stereotype, comment=comment)
            for comment in data.comments
        ]
        return record(data, stereotype=stereotype, stereotype_votes=votes)


ClusterRecipes.update_globals(globals())
