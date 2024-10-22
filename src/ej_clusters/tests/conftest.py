import pytest
from django.test import Client, RequestFactory

from ej_clusters.models.cluster import Cluster
from ej_clusters.models.clusterization import Clusterization
from ej_clusters.models.stereotype import Stereotype
from ej_clusters.models.stereotype_vote import StereotypeVote
from ej_conversations.enums import Choice
from ej_users.models import User
from ej_conversations.tests.conftest import *


@pytest.fixture
def stereotype(db, user):
    return Stereotype.objects.create(name="stereotype", owner=user)


@pytest.fixture
def stereotype_vote(db, comment, stereotype):
    return StereotypeVote.objects.create(
        author=stereotype, comment=comment, choice=Choice.AGREE
    )


@pytest.fixture
def clusterization(db, conversation):
    return Clusterization.objects.create(conversation=conversation)


@pytest.fixture
def cluster(db, clusterization, stereotype):
    cluster = Cluster.objects.create(clusterization=clusterization, name="My Cluster")
    cluster.stereotypes.add(stereotype)
    cluster.save()
    return cluster


@pytest.fixture
def request_factory(self):
    return RequestFactory()


@pytest.fixture
def admin_user(db):
    admin_user = User.objects.create_superuser("admin@test.com", "pass")
    admin_user.save()
    return admin_user


@pytest.fixture
def request_as_admin(request_factory, admin_user):
    request = request_factory
    request.user = admin_user
    return request


@pytest.fixture
def logged_client(user):
    client = Client()
    client.force_login(user)
    return client
