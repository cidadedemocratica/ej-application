from ej_campaigns.middleware import redirect_to_login_page
from django.test import Client
from mock import Mock

class TestMiddleware:

    def test_redirect_to_login_when_user_answer_campaign(self, board, conversation, comment):
        board.add_conversation(conversation)
        board_slug = board.slug;
        conversation_slug = conversation.slug
        url = '/{}/conversations/{}/'.format(board_slug, conversation_slug)
        c = Client()
        response = c.get(url, {'comment_id': comment.id, 'vote': 'agree','origin': 'campaign'})
        login_url = url + '&comment_id={}&vote={}'.format(comment.id, 'agree')
        assert response.url == '/login?next=' + login_url 
