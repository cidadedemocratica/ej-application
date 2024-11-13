import json

import mock
import pytest
from django.contrib.auth.models import AnonymousUser
from django.test.client import Client
from rest_framework.test import APIClient

from ej_boards.models import Board
from ej_conversations import create_conversation
from ej_users.models import User

API_V1_URL = "/api/v1"


def get_authorized_api_client(user_info):
    api = APIClient()
    response = api.post(API_V1_URL + "/login/", user_info, format="json")
    access_token = response.json()["access_token"]
    api.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)
    return api


@pytest.fixture
def user(db):
    user = User.objects.create_user("email@server.com", "password")
    user.board_name = "testboard"

    # TODO: Fix this dirty way to set user permissions
    def has_perm(self, x, y=None):
        return True  # Modify the function body as needed

    user.has_perm = has_perm.__get__(user)

    user.save()
    return user


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def conversation(db, user):  # noqa: F811
    conversation_object = create_conversation(
        text="test", title="title", author=user, is_promoted=True, anonymous_votes=1
    )
    yield conversation_object
    conversation_object.delete()


@pytest.fixture
def comment(db, conversation, user):  # noqa: F811
    comment_object = conversation.create_comment(user, "content", "approved")
    yield comment_object
    comment_object.delete()


@pytest.fixture
def comments(db, conversation, user):  # noqa: F811
    comment_object_1 = conversation.create_comment(user, "content 1", "approved")
    comment_object_2 = conversation.create_comment(user, "content 2", "approved")
    yield [comment_object_1, comment_object_2]
    map(lambda x: x.delete(), [comment_object_1, comment_object_2])


@pytest.fixture
def vote(db, user, comment):  # noqa: F811
    vote_object = comment.vote(author=user, choice="agree")
    yield vote_object
    vote_object.delete()


@pytest.fixture
def board(user):  # noqa: F811
    board = Board.objects.create(slug="userboard", owner=user, description="board")
    return board


@pytest.fixture
def post_request(rf):
    request = rf.post("")
    request.user = AnonymousUser()
    return request


@pytest.fixture
def request_(rf):
    request = rf.get("")
    request.user = AnonymousUser()
    return request


@pytest.fixture
def request_with_user(rf, user):  # noqa: F811
    request = rf.get("/testboard/")
    request.user = user
    return request


@pytest.fixture
def custom_request():
    REQUEST_META = {"HTTP_X_FORWARDED_PROTO": "", "HTTP_HOST": "localhost:8000"}
    request = mock.Mock()
    request.META = REQUEST_META
    return request


@pytest.fixture
def mk_user(db, email="default@user.com", is_staff=False):
    return User.objects.create_user(email, "1234", is_staff=is_staff)


@pytest.fixture
def api(client):
    return ApiClient(client)


@pytest.fixture
def conversation_with_comments(conversation, board):
    user1 = User.objects.create_user("user1@email.br", "password")
    user2 = User.objects.create_user("user2@email.br", "password")
    user3 = User.objects.create_user("user3@email.br", "password")

    board.save()
    conversation.board = board
    conversation.save()

    comment = conversation.create_comment(
        conversation.author, "aa", status="approved", check_limits=False
    )
    comment2 = conversation.create_comment(
        conversation.author, "aaa", status="approved", check_limits=False
    )
    comment3 = conversation.create_comment(
        conversation.author, "aaaa", status="approved", check_limits=False
    )
    comment4 = conversation.create_comment(
        conversation.author, "test", status="approved", check_limits=False
    )

    comment.vote(user1, "agree")
    comment.vote(user2, "agree")
    comment.vote(user3, "agree")

    comment2.vote(user1, "disagree")
    comment2.vote(user2, "agree")
    comment2.vote(user3, "agree")

    comment3.vote(user1, "disagree")
    comment3.vote(user2, "disagree")
    comment3.vote(user3, "agree")

    comment4.vote(user1, "disagree")
    comment4.vote(user2, "disagree")
    comment4.vote(user3, "disagree")
    conversation.save()
    return conversation


@pytest.fixture()
def conversation_with_votes(conversation, board):
    user1 = User.objects.create_user("user1@email.br", "password")
    user2 = User.objects.create_user("user2@email.br", "password")
    user3 = User.objects.create_user("user3@email.br", "password")

    conversation.board = board
    conversation.save()

    comment = conversation.create_comment(
        conversation.author, "aa", status="approved", check_limits=False
    )
    comment.vote(user1, "agree")
    comment.vote(user2, "agree")
    comment.vote(user3, "disagree")
    return conversation


class ApiClient:
    def __init__(self, client: Client):
        self.client = client
        self.response = None

    def _result(self, data, fields=None, exclude=(), skip=()):
        if fields is not None:
            data = {k: v for k, v in data.items() if k in fields}
        for field in exclude:
            del data[field]
        for field in skip:
            data.pop(field, None)
        return data

    def _prepare(self, data):
        if isinstance(data, bytes):
            return data
        return json.dumps(data).encode("utf8")

    def get(self, url, raw=False, **kwargs):
        response = self.client.get(url)
        self.response = response
        data = response if raw else response.data
        return self._result(data, **kwargs)

    def post(self, url, data, **kwargs):
        data = self._prepare(data)
        response = self.client.post(url, data, content_type="application/json")
        self.response = response
        obj = json.loads(response.content)
        return self._result(obj, **kwargs)
