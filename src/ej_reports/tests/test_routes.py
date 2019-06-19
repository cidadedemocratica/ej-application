import pytest, csv, io
from django.test import RequestFactory
from ej.testing import UrlTester

from ej_clusters.models import Stereotype, StereotypeVote, Cluster
from ej_conversations.models import Conversation, Choice
from ej.routes import index
from ej_users.models import User

BASE_URL = '/api/v1'

@pytest.fixture
def request_factory():
    return RequestFactory()

@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser('admin@server.com', '1234', name='admin')

@pytest.fixture
def request_as_admin(request_factory, admin_user):
    request = request_factory
    request.user = admin_user
    return request

@pytest.fixture
def conversation(admin_user):
    return Conversation.objects.create(title='Title', author=admin_user)

@pytest.fixture
def comment(conversation, admin_user):
    return conversation.create_comment(admin_user, 'comment', 'approved')

@pytest.fixture
def stereotype(conversation, admin_user, comment):
    stereotype = Stereotype.objects.create(name='stereo', conversation=conversation, owner=admin_user)
    StereotypeVote.objects.create(author=stereotype, choice=Choice.SKIP, comment=comment)
    return stereotype

@pytest.fixture
def cluster(conversation, admin_user):
    cluster = Cluster.objects.create(clusterization=conversation.clusterization, name='cluster')
    return cluster


class TestRoutes(UrlTester):
    user_urls = [
        '/conversations/title/reports/',
        '/conversations/title/reports/scatter/',
        '/conversations/title/reports/data/clusters/cluster.csv',
    ]
    admin_urls = [
        '/conversations/title/reports/participants/',
    ]

    @pytest.fixture
    def data(self, conversation, author_db, stereotype, cluster):
        conversation.author = author_db
        conversation.save()
        stereotype.owner = author_db
        stereotype.conversation = conversation
        stereotype.save()
        cluster.save()
        return {
            'conversation': conversation.__dict__,
            'author': author_db.__dict__,
            'stereotype': stereotype.__dict__,
        }

    def test_report_empty_cluster_csv_route(self, request_as_admin, conversation, cluster):
        path = BASE_URL + f'/conversations/{conversation.slug}/reports/data/clusters/{cluster.name}.csv'
        request = request_as_admin
        request.get(path)
        response = index(request)

        assert response.status_code == 302

        content = response.content.decode('utf-8')
        csv_out = list(csv.reader(io.StringIO(content)))
        assert len(csv_out) == 0

