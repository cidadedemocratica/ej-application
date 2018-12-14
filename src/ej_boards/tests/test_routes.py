import pytest
from django.http import Http404
from django.test import TestCase, Client

from ej.testing import UrlTester
from ej_boards import routes
from ej_boards.models import Board
from ej_boards.mommy_recipes import BoardRecipes
from ej_conversations.models import Comment
from ej_conversations.models.utils import votes_counter
from ej_conversations.mommy_recipes import ConversationRecipes
from ej_users.models import User


@pytest.fixture
def user(db):
    user = User.objects.create_user('email@server.com', 'password')
    user.save()
    return user


@pytest.fixture
def board(db, user):
    user.save()
    board = Board.objects.create(owner=user, title='tiel', slug='slugs')
    board.save()
    return board


class TestRoutes(UrlTester, BoardRecipes, ConversationRecipes):
    public_urls = [
        '/board-slug/conversations/',
        '/board-slug/conversations/conversation/'
    ]
    user_urls = [
        '/board-slug/conversations/conversation/reports/',
        '/board-slug/conversations/conversation/reports/scatter/',
        '/profile/boards/add/',
        '/profile/boards/',
    ]
    owner_urls = [
        '/board-slug/conversations/add/',
        '/board-slug/conversations/conversation/edit/',
        '/board-slug/conversations/conversation/moderate/',
        '/board-slug/conversations/conversation/stereotypes/',
        '/board-slug/conversations/conversation/stereotypes/add/'
    ]

    @pytest.fixture
    def data(self, conversation, author_db, board):
        board.owner = author_db
        board.save()
        conversation.author = author_db
        conversation.save()
        board.add_conversation(conversation)


class TestBoardConversationRoutes(ConversationRecipes):
    def test_create_conversation(self, rf, board):
        request = rf.post('', {'title': 'whatever', 'tags': 'tag', 'text': 'description', 'comments_count': 0})
        request.user = board.owner
        response = routes.conversation_create(request, board)
        assert response.status_code == 302
        assert response.url == '/slugs/conversations/whatever/stereotypes/'

    def test_create_invalid_conversation(self, rf, board):
        request = rf.post('', {'title': '', 'tags': 'tag', 'text': 'description', 'comments_count': 0})
        request.user = board.owner
        response = routes.conversation_create(request, board)
        assert not response['form'].is_valid()

    def test_edit_conversation(self, rf, board, db, conversation):
        conversation.author = board.owner
        conversation.save()
        request = rf.post('', {'title': 'whatever', 'tags': 'tag', 'text': 'description', 'comments_count': 0})
        request.user = conversation.author
        conversation.is_promoted = False
        board.add_conversation(conversation)
        response = routes.conversation_edit(request, board, conversation)
        assert response.status_code == 302
        assert response.url == '/slugs/conversations/conversation/moderate/'
        assert routes.report(request, board, conversation)

    def test_edit_invalid_conversation(self, rf, db, board, conversation):
        conversation.author = board.owner
        conversation.save()
        request = rf.post('', {'title': '', 'tags': 'tag', 'text': 'description', 'comments_count': 0})
        request.user = conversation.author
        conversation.is_promoted = False
        board.add_conversation(conversation)
        response = routes.conversation_edit(request, board, conversation)
        assert not response['form'].is_valid()

    def test_edit_conversation_not_in_board(self, rf, db, board, conversation):
        conversation.author = board.owner
        conversation.save()
        request = rf.post('', {'title': '', 'tags': 'tag', 'text': 'description', 'comments_count': 0})
        with pytest.raises(Http404):
            routes.conversation_edit(request, board, conversation)

    def test_conversation_detail(self, rf, db, board, conversation):
        conversation.author = board.owner
        conversation.save()
        request = rf.get('', {})
        request.user = conversation.author
        conversation.is_promoted = False
        board.add_conversation(conversation)
        response = routes.conversation_detail(request, board, conversation)
        assert response['conversation'] == conversation
        assert response['can_comment']
        assert response['can_edit']

    def test_conversation_detail_post_comment(self, rf, db, board, conversation):
        user = board.owner
        conversation.author = user
        conversation.save()
        request = rf.post('', {'action': 'comment', 'content': 'test comment'})
        request.user = conversation.author
        conversation.is_promoted = False
        board.add_conversation(conversation)
        response = routes.conversation_detail(request, board, conversation)
        assert response['conversation'] == conversation
        assert response['can_comment']
        assert response['can_edit']
        assert Comment.objects.filter(author=user)[0].content == 'test comment'

    def test_conversation_detail_vote_comment(self, rf, db, board, conversation):
        user = board.owner
        conversation.author = user
        conversation.save()
        comment = conversation.create_comment(user, 'comment')
        request = rf.post('', {'action': 'vote', 'vote': 'agree', 'comment_id': comment.id})
        request.user = conversation.author
        conversation.is_promoted = False
        board.add_conversation(conversation)
        response = routes.conversation_detail(request, board, conversation)
        assert response['conversation'] == conversation
        assert response['can_comment']
        assert response['can_edit']
        assert votes_counter(comment) == 1

    def test_conversation_detail_not_in_board(self, rf, db, board, conversation):
        conversation.author = board.owner
        conversation.save()
        request = rf.post('', {'action': 'comment', 'content': 'test comment'})
        request.user = conversation.author
        with pytest.raises(Http404):
            routes.conversation_detail(request, board, conversation)

    def test_get_moderate_conversation_not_in_board(self, rf, db, board, conversation):
        conversation.author = board.owner
        conversation.save()
        request = rf.get('', {})
        request.user = conversation.author
        with pytest.raises(Http404):
            routes.conversation_moderate(request, board, conversation)


class TestBoardViewRoutest:
    def test_get_create_board(self, rf, user):
        request = rf.get('', {})
        request.user = user
        response = routes.board_create(request)
        assert response['content_title']
        assert response['form']

    def test_post_create_valid_board(self, rf, user):
        data = {'slug': 'slug',
                'title': 'new title',
                'description': 'description',
                'palette': 'Blue'}
        request = rf.post('', data)
        request.user = user
        response = routes.board_create(request)
        assert response.url == '/slug/'
        assert response.status_code == 302

        data = {'slug': 'slug2',
                'title': 'new title',
                'description': 'description'}
        request = rf.post('', data)
        request.user = user
        with pytest.raises(Http404):
            routes.board_create(request)

    def test_post_create_invalid_board(self, rf, user):
        data = {'slug': '',
                'title': 'new title',
                'description': 'description'}
        request = rf.post('', data)
        request.user = user
        response = routes.board_create(request)
        assert not response['form'].is_valid()
        assert response['content_title']

    def test_list_board_only_one_board(self, rf, user, board):
        board.owner = user
        request = rf.get('', {})
        request.user = user
        response = routes.board_list(request)
        assert response.status_code == 302
        assert response.url == board.get_absolute_url() + 'conversations/'


class TestBoardRoutes(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('name@server.com', '1234', name='name')
        client = Client()
        client.force_login(self.user)
        self.logged_client = client

    def test_list_profile_boards(self):
        client = self.logged_client
        response = client.get('/profile/boards/')
        self.assertTrue(response.status_code, 200)

    def test_list_profile_board_anonymous_user(self):
        client = Client()
        response = client.get('/profile/boards/')
        self.assertRedirects(response, '/login/?next=/profile/boards/', 302, 200)

    def test_create_board(self):
        client = self.logged_client
        data = {'slug': 'slug',
                'title': 'new title',
                'description': 'description',
                'palette': 'Blue'}
        response = client.post('/profile/boards/add/', data=data)
        self.assertRedirects(response, '/slug/', 302, 200)

    def test_create_invalid_board(self):
        client = self.logged_client
        data = {'slug': 's', 'title': 'title', 'description': ''}
        response = client.post('/profile/boards/add/', data=data)
        self.assertTrue(response.status_code, 200)

    def test_get_create_board(self):
        client = self.logged_client
        response = client.get('/profile/boards/add')
        self.assertTrue(response.status_code, 200)

    def test_create_board_anonymous_user(self):
        client = Client()
        response = client.get('/profile/boards/add/')
        self.assertRedirects(response, '/login/?next=/profile/boards/add/', 302, 200)

    def test_edit_board_anonymous_user(self):
        client = Client()
        Board.objects.create(slug='slug1', title='title1', owner=self.user)
        response = client.get('/slug1/edit/')
        self.assertTrue(response.status_code, 404)

    def test_edit_board_logged_user(self):
        client = self.logged_client
        Board.objects.create(slug='slug1',
                             title='title1',
                             owner=self.user,
                             palette='orange')
        data = {'slug': 'slug1', 'title': 'new title', 'palette': 'pink'}
        response = client.post('/slug1/edit/', data=data)
        self.assertTrue(response.status_code, 200)
        # self.assertRedirects(response, '/slug1/', 302, 200)

    def test_edit_invalid_board_logged_user(self):
        client = self.logged_client
        Board.objects.create(slug='slug1', title='title1', owner=self.user)
        data = {'slug': 'slug1'}
        response = client.post('/slug1/edit/', data=data)
        self.assertTrue(response.status_code, 200)
