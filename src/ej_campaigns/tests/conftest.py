import json
import pytest

from django.test.client import Client
from django.contrib.auth.models import AnonymousUser

from ej_conversations import create_conversation
from ej_users.models import User
from ej_boards.models import Board


@pytest.fixture
def user(db):
    user = User.objects.create_user('email@server.com', 'password')
    user.board_name = 'testboard'

    # TODO: Fix this dirty way to set user permissions
    user.has_perm = lambda x, y=None: True

    user.save()
    return user


@pytest.fixture
def conversation(db, user):
    return create_conversation(text='test',
                               title='mautic conversation template',
                               author=user,
                               is_promoted=True)


@pytest.fixture
def comment(db, conversation, user):
    return conversation.create_comment(user, 'content', 'approved')

@pytest.fixture
def board(db, user):
    return Board.objects.create(slug='slug1',
                            title='title1',
                            owner=user,
                            palette='orange')

@pytest.fixture
def post_request(rf):
    request = rf.post('')
    request.user = AnonymousUser()
    return request


@pytest.fixture
def request_(rf):
    request = rf.get('')
    request.user = AnonymousUser()
    return request


@pytest.fixture
def request_with_user(rf, user):
    request = rf.get('/testboard/')
    request.user = user
    return request
