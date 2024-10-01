import pytest
from django.utils.translation import gettext as _
from ej_clusters.forms import StereotypeForm, StereotypeVoteForm
from ej_clusters.models import Stereotype
from ej_clusters.mommy_recipes import ClusterRecipes
from ej_conversations.enums import Choice
from ej_conversations.tests.test_views import ConversationSetup


class TestStereotypeForm(ClusterRecipes):
    def test_valid_data(self, user_db):
        name = "Stereotype"
        description = "description"

        form = StereotypeForm(
            {"name": name, "description": description},
            owner=user_db,
            clusterization=self.clusterization.make(),
        )
        assert form.is_valid()
        stereotype = form.save()
        assert stereotype.name == name
        assert stereotype.description == description

        cluster = stereotype.clusters.first()
        assert cluster.name == name
        assert cluster.description == description

    def test_blank_data(self, user_db):
        form = StereotypeForm({}, owner=user_db)
        assert not form.is_valid()
        assert form.errors == {"name": [_("This field is required.")]}

    def test_edit_existing_stereotype(self, user_db):
        instance = Stereotype.objects.create(name="Stereotype1", owner=user_db)
        form = StereotypeForm(
            {"name": "Stereotype1", "description": "description"},
            instance=instance,
            clusterization=self.clusterization.make(),
        )
        assert form.is_valid()
        stereotype = form.save()
        cluster = stereotype.clusters.first()
        assert stereotype.name == cluster.name
        assert stereotype.description == cluster.description

    def test_repetead_stereotype_data(self, user_db):
        Stereotype.objects.create(name="Stereotype1", owner=user_db)
        form = StereotypeForm(
            {"name": "Stereotype1", "description": "description"}, owner=user_db
        )
        assert not form.is_valid()
        assert set(form.errors) == {"__all__"}


class TestStereotypeVoteForm(ConversationSetup):
    def test_valid_data(self, base_user, conversation_with_comments):
        comment = conversation_with_comments.comments.first()
        stereotype, _ = Stereotype.objects.get_or_create(name="name", owner=base_user)
        form = StereotypeVoteForm(
            data={"comment": comment.id, "choice": Choice.AGREE},
            stereotype=stereotype,
            comments_queryset=conversation_with_comments.comments.all(),
            initial={"comment": comment},
        )
        assert form.is_valid()
        stereotype_vote = form.save(form["choice"].value(), form["comment"].value())
        assert stereotype_vote.comment == comment
        assert stereotype_vote.choice == Choice.AGREE

    def test_not_sending_comment_queryset(self, conversation_with_comments):
        comment = conversation_with_comments.comments.first()
        form = StereotypeVoteForm(
            data={"comment": comment.id, "choice": Choice.DISAGREE},
            initial={"comment": comment},
        )
        with pytest.raises(AttributeError):
            form.is_valid()
