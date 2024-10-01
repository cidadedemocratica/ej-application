from ej_conversations.enums import Choice
import pytest
from boogie.testing.pytest import UrlTester
from django.test import Client
from django.urls import reverse
from django.template.exceptions import TemplateDoesNotExist
from ej_clusters.enums import ClusterStatus
from ej_clusters.models.cluster import Cluster
from ej_clusters.models.stereotype import Stereotype
from ej_clusters.mommy_recipes import ClusterRecipes
from ej_clusters.models.stereotype_vote import StereotypeVote
from ej_clusters.models.clusterization import Clusterization
from ej_conversations.mommy_recipes import ConversationRecipes
from ej_conversations.tests.test_views import ConversationSetup


@pytest.fixture
def conversation_with_comments(conversation, base_board, base_user):
    conversation.author = base_user
    base_board.owner = base_user
    base_board.save()
    conversation.board = base_board
    conversation.save()

    conversation.create_comment(base_user, "aa", status="approved", check_limits=False)

    conversation.create_comment(base_user, "aaa", status="approved", check_limits=False)
    conversation.create_comment(base_user, "aaaa", status="approved", check_limits=False)

    conversation.save()
    return conversation


@pytest.fixture
def stereotype(base_user):
    stereotype, _ = Stereotype.objects.get_or_create(name="name", owner=base_user)
    stereotype.save()
    return stereotype


@pytest.fixture
def stereotype_with_clusterization(conversation_with_comments, base_user):
    clusterization = Clusterization.objects.create(
        conversation=conversation_with_comments, cluster_status=ClusterStatus.ACTIVE
    )
    cluster = Cluster.objects.create(name="name", clusterization=clusterization)
    stereotype, _ = Stereotype.objects.get_or_create(name="name", owner=base_user)
    cluster.stereotypes.add(stereotype)

    return stereotype


class TestRoutes(ConversationRecipes, UrlTester):
    user_urls = ["/stereotypes/"]
    owner_urls = ["/conversations/1/conversation/stereotypes/"]

    @pytest.fixture
    def data(self, conversation, board, author_db):
        conversation.author = author_db
        board.owner = author_db
        board.save()
        conversation.board = board
        conversation.save()


class TestStereotypeVoteList(ClusterRecipes, ConversationSetup):
    @pytest.fixture
    def conversation_with_board(self, conversation, board, user_db):
        conversation.author = user_db
        board.owner = user_db
        board.save()
        conversation.board = board
        conversation.save()
        return conversation

    def build_formset_post_information(self, comments, stereotype):
        choices = Choice.values
        comments_dict = {}
        for i, comment in enumerate(comments):
            comments_dict[f"create-{i}-choice"] = [choices[i]]
            comments_dict[f"create-{i}-comment"] = [comment.id]
            comments_dict[f"create-{i}-id"] = [""]

        return {
            **{
                "stereotype_id": [str(stereotype.id)],
                "create-TOTAL_FORMS": ["3"],
                "create-INITIAL_FORMS": ["0"],
                "create-MIN_NUM_FORMS": ["0"],
                "create-MAX_NUM_FORMS": ["1000"],
            },
            **comments_dict,
        }

    def test_get_stereotype_vote_page_without_stereotypes(
        self, conversation_with_board, user_db, rf
    ):
        Clusterization.objects.create(
            conversation=conversation_with_board, cluster_status=ClusterStatus.ACTIVE
        )

        client = Client()
        client.force_login(user_db)

        path = reverse(
            "boards:stereotype-votes-list",
            kwargs={
                "board_slug": conversation_with_board.board.slug,
                "conversation_id": conversation_with_board.id,
                "slug": conversation_with_board.slug,
            },
        )
        response = client.get(path)

        assert response.status_code == 200

    def test_get_stereotypes_of_conversation_without_clusters(
        self, conversation_with_board, user_db, rf
    ):
        client = Client()
        client.force_login(user_db)

        path = reverse(
            "boards:stereotype-votes-list",
            kwargs={
                "board_slug": conversation_with_board.board.slug,
                "conversation_id": conversation_with_board.id,
                "slug": conversation_with_board.slug,
            },
        )
        response = client.get(path)

        assert response.status_code == 200

    def test_get_stereotype_vote_page_with_stereotype(
        self, conversation_with_board, user_db, rf
    ):
        clusterization = Clusterization.objects.create(
            conversation=conversation_with_board, cluster_status=ClusterStatus.ACTIVE
        )
        cluster = Cluster.objects.create(name="name", clusterization=clusterization)
        stereotype, _ = Stereotype.objects.get_or_create(name="name", owner=user_db)
        cluster.stereotypes.add(stereotype)

        client = Client()
        client.force_login(user_db)

        path = reverse(
            "boards:stereotype-votes-list",
            kwargs={
                "board_slug": conversation_with_board.board.slug,
                "conversation_id": conversation_with_board.id,
                "slug": conversation_with_board.slug,
            },
        )
        response = client.get(path)

        assert response.status_code == 200

    def test_get_stereotype_vote_page_with_stereotypes_selected(
        self, conversation_with_board, user_db, rf
    ):
        clusterization = Clusterization.objects.create(
            conversation=conversation_with_board, cluster_status=ClusterStatus.ACTIVE
        )

        cluster = Cluster.objects.create(name="name", clusterization=clusterization)
        stereotype, _ = Stereotype.objects.get_or_create(name="name", owner=user_db)
        second_stereotype, _ = Stereotype.objects.get_or_create(
            name="second stereotype", owner=user_db
        )
        cluster.stereotypes.add(stereotype)
        cluster.stereotypes.add(second_stereotype)

        client = Client()
        client.force_login(user_db)

        path = reverse(
            "boards:stereotype-votes-list",
            kwargs={
                "board_slug": conversation_with_board.board.slug,
                "conversation_id": conversation_with_board.id,
                "slug": conversation_with_board.slug,
            },
        )
        response = client.get(path, {"stereotype-select": second_stereotype.id})

        assert response.status_code == 200

    def test_create_valid_stereotype_votes_admin(
        self, conversation_with_comments, admin_user, stereotype_with_clusterization
    ):
        client = Client()
        client.force_login(admin_user)

        path = reverse(
            "boards:stereotype-votes-list",
            kwargs={
                "board_slug": conversation_with_comments.board.slug,
                "conversation_id": conversation_with_comments.id,
                "slug": conversation_with_comments.slug,
            },
        )

        comments = conversation_with_comments.comments.all()
        data = self.build_formset_post_information(
            comments, stereotype_with_clusterization
        )
        response = client.post(path, data)

        votes = StereotypeVote.objects.filter(author=stereotype_with_clusterization)

        assert response.status_code == 200
        assert votes.exists()
        assert votes.count() == 3

    def test_create_valid_stereotype_votes_conversation_author(
        self, conversation_with_comments, base_user, stereotype_with_clusterization
    ):
        client = Client()
        client.force_login(base_user)

        path = reverse(
            "boards:stereotype-votes-list",
            kwargs={
                "board_slug": conversation_with_comments.board.slug,
                "conversation_id": conversation_with_comments.id,
                "slug": conversation_with_comments.slug,
            },
        )

        comments = conversation_with_comments.comments.all()
        data = self.build_formset_post_information(
            comments, stereotype_with_clusterization
        )
        response = client.post(path, data)

        votes = StereotypeVote.objects.filter(author=stereotype_with_clusterization)

        assert response.status_code == 200
        assert votes.exists()
        assert votes.count() == 3

    def test_if_data_was_saved_correctly(
        self, conversation_with_comments, base_user, stereotype_with_clusterization
    ):
        client = Client()
        client.force_login(base_user)

        path = reverse(
            "boards:stereotype-votes-list",
            kwargs={
                "board_slug": conversation_with_comments.board.slug,
                "conversation_id": conversation_with_comments.id,
                "slug": conversation_with_comments.slug,
            },
        )

        comments = conversation_with_comments.comments.all()
        data = self.build_formset_post_information(
            comments, stereotype_with_clusterization
        )
        client.post(path, data)

        choices = Choice.values
        for i, comment in enumerate(comments):
            assert StereotypeVote.objects.filter(
                comment=comment, choice=choices[i]
            ).exists()

    def test_anonymous_user_access(self, conversation_with_comments):
        client = Client()
        path = reverse(
            "boards:stereotype-votes-list",
            kwargs={
                "board_slug": conversation_with_comments.board.slug,
                "conversation_id": conversation_with_comments.id,
                "slug": conversation_with_comments.slug,
            },
        )
        response = client.get(path)
        assert response.status_code == 302
        assert "/login/" in response.url


class TestStereotypeDelete(ConversationSetup):
    def test_get_access_delete_stereotype_view(self, base_user, stereotype):
        url = reverse("stereotypes:delete", kwargs={"pk": stereotype.id})

        client = Client()
        client.force_login(base_user)

        with pytest.raises(TemplateDoesNotExist):
            client.get(url)
        assert Stereotype.objects.filter(id=stereotype.id).exists()

    def test_delete_stereotype_with_no_permission(self, stereotype):
        url = reverse("stereotypes:delete", kwargs={"pk": stereotype.id})

        client = Client()
        response = client.post(url)

        assert response.status_code == 302
        assert "/login/" in response.url
        assert Stereotype.objects.filter(id=stereotype.id).exists()

    def test_delete_stereotype(self, base_user, stereotype, conversation_with_comments):
        url = reverse("stereotypes:delete", kwargs={"pk": stereotype.id})

        client = Client()
        client.force_login(base_user)
        clusters = stereotype.clusters
        response = client.post(url, {"conversation_id": conversation_with_comments.id})

        assert response.status_code == 302
        assert response.url == reverse(
            "boards:stereotype-votes-list",
            kwargs=conversation_with_comments.get_url_kwargs(),
        )
        assert not Stereotype.objects.filter(id=stereotype.id).exists()
        assert not Cluster.objects.filter(id__in=clusters).exists()

    def test_admin_delete_stereotype(
        self, admin_user, stereotype, conversation_with_comments
    ):
        url = reverse("stereotypes:delete", kwargs={"pk": stereotype.id})

        client = Client()
        client.force_login(admin_user)
        clusters = stereotype.clusters
        response = client.post(url, {"conversation_id": conversation_with_comments.id})

        assert response.status_code == 302
        assert response.url == reverse(
            "boards:stereotype-votes-list",
            kwargs=conversation_with_comments.get_url_kwargs(),
        )
        assert not Stereotype.objects.filter(id=stereotype.id).exists()
        assert not Cluster.objects.filter(id__in=clusters).exists()


class TestStereotypeEdit(TestStereotypeVoteList):
    @pytest.fixture
    def conversation_stereotype(self, base_user, conversation_with_board):
        stereotype, _ = Stereotype.objects.get_or_create(name="name", owner=base_user)
        stereotype.save()
        clusterization = Clusterization.objects.create(
            conversation=conversation_with_board, cluster_status=ClusterStatus.ACTIVE
        )
        clusterization.save()
        group = Cluster.objects.create(
            name=stereotype.name,
            description=stereotype.description,
            clusterization=clusterization,
        )
        group.save()
        group.stereotypes.add(stereotype)
        return stereotype

    def test_post_edit_stereotype(self, base_user, conversation_stereotype):
        url = reverse("stereotypes:edit", kwargs={"pk": conversation_stereotype.id})

        client = Client()
        client.force_login(base_user)

        new_name = "new name"
        response = client.post(
            url,
            {
                "name": new_name,
                "description": conversation_stereotype.description,
            },
        )
        conversation_stereotype.refresh_from_db()

        assert response.status_code == 200
        assert conversation_stereotype.name == new_name

    def test_post_edit_stereotype_without_required_field(
        self, base_user, conversation_stereotype
    ):
        url = reverse("stereotypes:edit", kwargs={"pk": conversation_stereotype.id})

        client = Client()
        client.force_login(base_user)

        response = client.post(url)
        conversation_stereotype.refresh_from_db()

        assert response.status_code == 200
        assert b"This field is required." in response.content


class TestStereotypeCreate(ConversationSetup):
    @pytest.fixture
    def clusterization(self, conversation):
        clusterization = Clusterization.objects.create(
            conversation=conversation, cluster_status=ClusterStatus.ACTIVE
        )
        clusterization.save()
        return clusterization

    def test_post_create_stereotype(self, clusterization, base_user):
        url = reverse(
            "stereotypes:create", kwargs={"clusterization_id": clusterization.id}
        )
        client = Client()
        client.force_login(base_user)

        name = "create stereotype"
        description = "description"
        response = client.post(
            url,
            {
                "name": name,
                "description": description,
            },
        )

        assert "integrateData" in response["HX-Trigger"]
        assert response.status_code == 200
        assert Stereotype.objects.filter(owner=base_user, name=name).exists()
        assert Cluster.objects.filter(name=name, description=description).exists()

    def test_post_create_stereotype_without_required_field(
        self, clusterization, base_user
    ):
        url = reverse(
            "stereotypes:create", kwargs={"clusterization_id": clusterization.id}
        )
        client = Client()
        client.force_login(base_user)

        response = client.post(
            url,
            {
                "name": "",
                "description": "description",
            },
        )

        assert response.status_code == 200
        assert "HX-Trigger" not in response
        assert not Stereotype.objects.filter(owner=base_user, name="").exists()
        assert not Cluster.objects.filter(name="", description="description").exists()


class TestClusterIndex(ConversationSetup, ClusterRecipes):
    def test_cluster_when_there_is_no_groups(self, conversation_db, admin_db):
        conversation_db.get_clusterization()
        url = reverse("boards:cluster-index", kwargs=conversation_db.get_url_kwargs())
        client = Client()
        client.force_login(admin_db)
        response = client.get(url)

        assert response.status_code == 200
        assert b"the graph will be generated and displayed here after" in response.content

    def test_cluster_without_permission(self, conversation_db, base_user):
        conversation_db.get_clusterization()
        url = reverse("boards:cluster-index", kwargs=conversation_db.get_url_kwargs())
        client = Client()
        client.force_login(base_user)
        response = client.get(url)

        assert response.status_code == 302
        assert response.url == "/login/"
