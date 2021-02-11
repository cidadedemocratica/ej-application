import pytest
from ej_conversations.mommy_recipes import ConversationRecipes
from ej.testing import UrlTester

from ej_conversations.routes_comments import comment_url
from ej_conversations import routes


class TestRoutes(UrlTester, ConversationRecipes):
    public_urls = ["/conversations/"]
    user_urls = [
        "/conversations/1/slug/",
        # '/comments/<id>-<hash>/'
    ]
    admin_urls = ["/conversations/add/"]
    owner_urls = ["/conversations/1/slug/edit/", "/conversations/1/slug/moderate/"]

    def get_data(self, request):
        conversation = request.getfixturevalue("conversation")
        conversation.author = request.getfixturevalue("author_db")
        conversation.is_promoted = True
        conversation.save()

    def test_can_view_user_url(self, user_client, comment_db):
        url = comment_url(comment_db)
        response = user_client.get(url)
        assert response.status_code == 200


class TestIntegrationsRoutes(ConversationRecipes):
    def test_get_tools(self, user_client, conversation_db, mk_user):
        response = user_client.get('/conversations/' + str(conversation_db.id)
                                   + '/' + conversation_db.slug + '/tools')
        assert response.status_code == 200
