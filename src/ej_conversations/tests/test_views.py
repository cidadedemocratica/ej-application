from pytest import raises
from django.http import HttpResponseServerError, Http404
from django.contrib.auth.models import AnonymousUser

from ej_conversations.models import Comment, FavoriteConversation
from ej_conversations.models.utils import votes_counter
from ej_conversations.routes import conversations, comments, admin
from ej_users.models import User


class TestConversationBase:
    def test_vote_in_comment(self, rf, conversation, comment, db):
        user = User.objects.create_user('user@server.com', 'password')
        conversation.comment = comment
        conversation.save()
        request = rf.post('', {'action': 'vote', 'vote': 'agree', 'comment_id': comment.id})
        request.user = user
        conversations.detail(request, conversation)
        assert votes_counter(comment) == 1

    def test_invalid_vote_in_comment(self, rf, conversation, comment):
        request = rf.post('', {'action': 'vote', 'vote': 'INVALID', 'comment_id': comment.id})
        user = User.objects.create_user('user@server.com', 'password')
        conversation = comment
        conversation.save()
        request.user = user
        with raises(Exception):
            conversations.detail(request, conversation)

    def test_invalid_action_conversation_detail(self, rf, conversation, comment):
        request = rf.post('', {'action': 'invalid'})
        user = User.objects.create_user('user@server.com', 'password')
        conversation.save()
        request.user = user
        response = conversations.detail(request, conversation)
        assert isinstance(response, HttpResponseServerError)

    def test_user_can_comment(self, rf, conversation):
        request = rf.post('', {'action': 'comment', 'content': 'test comment'})
        print(request)
        user = User.objects.create_user('user@server.com', 'password')
        request.user = user
        conversations.detail(request, conversation)
        assert Comment.objects.filter(author=user)[1].content == 'test comment'

    def test_user_post_invalid_comment(self, rf, conversation):
        request = rf.post('', {'action': 'comment', 'content': ''})
        user = User.objects.create_user('user@server.com', 'password')
        request.user = user
        response = conversations.detail(request, conversation)
        assert response['conversation']

    def test_anonymous_user_cannot_comment(self, rf, conversation):
        request = rf.post('', {'action': 'comment', 'content': 'test comment'})
        request.user = AnonymousUser()
        with raises(PermissionError):
            conversations.detail(request, conversation)

    def test_user_can_add_conversation_as_favorite(self, rf, user, conversation):
        request = rf.post('', {'action': 'favorite'})
        request.user = user
        conversations.detail(request, conversation)
        assert FavoriteConversation.objects.filter(user=user, conversation=conversation).exists()


class TestConversationComments:
    def test_user_can_get_all_his_comments(self, request_with_user, conversation, user, comment):
        ctx = comments.comment_list(request_with_user, conversation)
        assert len(ctx['approved']) == 1
        assert len(ctx['rejected']) == 0
        assert len(ctx['pending']) == 0
        assert ctx['can_edit']
        assert ctx['can_comment']

    def test_user_can_get_detail_of_a_comment(self, conversation, comment):
        ctx = comments.comment_detail(conversation, comment)
        assert ctx['comment'] is comment

    def test_comment_list_not_promoted_convesation(self, request_with_user, conversation, user):
        conversation.is_promoted = False
        with raises(Http404):
            comments.comment_list(request_with_user, conversation)

    def test_udetail_of_a_comment_not_promoted(self, conversation, comment):
        conversation.is_promoted = False
        with raises(Http404):
            comments.comment_detail(conversation, comment)

    def test_return_comment_passing_comment_id(self, rf, user, conversation, comment):
        comment_1 = conversation.create_comment(user, 'comment 1', 'approved')
        comment_2 = conversation.create_comment(user, 'comment 2', 'approved')
        request = rf.get('', {'action': 'vote',
                               'comment_id': comment_1.id,
                               'vote': 'agree',
                               'origin': 'mail'})
        request.user = user
        ctx = conversations.detail(request, conversation)
        assert ctx['comment'] == comment_1

    def test_return_not_voted_comment_passing_comment_id(self, rf, user, conversation, comment):
        comment_1 = conversation.create_comment(user, 'comment 1', 'approved')
        comment_2 = conversation.create_comment(user, 'comment 2', 'approved')
        request = rf.post('', {'action': 'vote',
                               'vote': 'agree',
                               'comment_id': comment_1.id})
        request.user = user
        conversations.detail(request, conversation)
        request = rf.get('', {'action': 'vote',
                               'comment_id': comment_1.id,
                               'vote': 'agree',
                               'origin': 'mail'})
        request.user = user
        ctx = conversations.detail(request, conversation)
        assert ctx['comment'] != comment_1




class TestAdminViews:
    def test_create_conversation(self, rf, user):
        request = rf.post('', {'title': 'whatever', 'tags': 'tag', 'text': 'description', 'comments_count': 0})
        request.user = user
        response = admin.create(request)
        assert response.status_code == 302
        assert response.url == '/conversations/whatever/stereotypes/'

    def test_create_invalid_conversation(self, rf, user):
        request = rf.post('', {'title': '', 'tags': 'tag', 'text': 'description', 'comments_count': 0})
        request.user = user
        response = admin.create(request)
        assert not response['form'].is_valid()

    def test_edit_conversation(self, rf, conversation):
        request = rf.post('', {'title': 'whatever', 'tags': 'tag', 'text': 'description', 'comments_count': 0})
        request.user = conversation.author
        response = admin.edit(request, conversation)
        assert response.status_code == 302
        assert response.url == '/conversations/title/moderate/'

    def test_edit_invalid_conversation(self, rf, conversation):
        request = rf.post('', {'title': '', 'tags': 'tag', 'text': 'description', 'comments_count': 0})
        request.user = conversation.author
        response = admin.edit(request, conversation)
        assert not response['form'].is_valid()

    def test_edit_not_promoted_conversation(self, rf, conversation):
        request = rf.post('', {})
        request.user = conversation.author
        conversation.is_promoted = False
        with raises(Http404):
            admin.edit(request, conversation)

    def test_get_edit_conversation(self, rf, conversation):
        user = conversation.author
        comment = conversation.create_comment(user, 'comment', 'pending')
        conversation.create_comment(user, 'comment1')
        comment.status = comment.STATUS.pending
        comment.save()
        request = rf.get('', {})
        request.user = user
        conversation.refresh_from_db()
        response = admin.edit(request, conversation)
        assert response['comments'][0] == comment
        assert response['conversation'] == conversation

    def test_author_can_moderate_conversation_approving_comment(self, rf, conversation):
        other = User.objects.create_user('email@email.br', 'pass')
        comment = conversation.create_comment(other, 'aa', check_limits=False)
        assert comment.status == comment.STATUS.pending
        request = rf.post('', {'comment': comment.id, 'vote': 'approve'})
        request.user = User.objects.get(email='email@server.com')
        admin.moderate(request, conversation)
        comment.refresh_from_db()
        assert comment.status == comment.STATUS.approved

    def test_author_can_moderate_conversation_rejecting_comment(self, rf, conversation):
        other = User.objects.create_user('email@email.br', 'pass')
        comment = conversation.create_comment(other, 'aa', check_limits=False)
        assert comment.status == comment.STATUS.pending
        request = rf.post('', {'comment': comment.id, 'vote': 'disapprove', 'rejection_reason': 'offensive_language'})
        request.user = User.objects.get(email='email@server.com')
        admin.moderate(request, conversation)
        comment.refresh_from_db()
        assert comment.status == comment.STATUS.rejected

    def test_get_moderate_conversation(self, rf, conversation):
        user = conversation.author
        other_user = User.objects.create_user('email@email.br', 'pass')
        comment = conversation.create_comment(other_user, 'aa', check_limits=False)
        assert comment.status == comment.STATUS.pending
        request = rf.get('', {})
        request.user = user
        response = admin.moderate(request, conversation)
        assert response['comments'][0] == comment

    def test_author_try_moderate_invalid_vote(self, rf, conversation):
        other = User.objects.create_user('email@email.br', 'pass')
        comment = conversation.create_comment(other, 'aa', check_limits=False)
        request = rf.post('', {'comment': comment.id, 'vote': 'other', 'rejection_reason': 'offensive_language'})
        request.user = User.objects.get(email='email@server.com')
        response = admin.moderate(request, conversation)
        assert isinstance(response, HttpResponseServerError)

    def test_author_try_moderate_unpromoted_conversation(self, rf, conversation):
        request = rf.get('')
        request.user = User.objects.get(email='email@server.com')
        conversation.is_promoted = False
        conversation.save()
        with raises(Http404):
            admin.moderate(request, conversation)
