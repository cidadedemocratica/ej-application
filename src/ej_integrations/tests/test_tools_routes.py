from ej_conversations.mommy_recipes import ConversationRecipes
from django.test import Client
from ej_integrations.models import RasaConversation
import pytest

TEST_DOMAIN = "https://domain.com.br"
CONVERSATION_BOARD_URL = "/board-slug/conversations"


class TestIntegrationsRoutes(ConversationRecipes):
    def setup_method(self):
        self.ROUTES = [
            "tools",
            "tools/chatbot",
            "tools/chatbot/webchat",
            "tools/telegram",
            "tools/chatbot/whatsapp",
        ]

    def test_do_not_get_tools_routes(self, user_client, conversation_db):
        for route in self.ROUTES:
            response = user_client.get(conversation_db.get_absolute_url() + route)
            assert response.status_code == 302

    def test_get_tools_routes(self, conversation_db):
        client = Client()
        client.force_login(conversation_db.author)
        for route in self.ROUTES:
            response = client.get(conversation_db.get_absolute_url() + route)
            assert response.status_code == 200


class TestRemoveRasaConnection(ConversationRecipes):
    def setup_method(self):
        self.PATH = "tools/chatbot/webchat/delete/"

    def test_superuser_delete_connection(self, conversation_db, admin_client):
        connection = RasaConversation.objects.create(
            conversation=conversation_db, domain=TEST_DOMAIN
        )
        connection_id = connection.id
        response = admin_client.get(
            conversation_db.get_absolute_url() + self.PATH + str(connection_id)
        )

        assert response.status_code == 302
        assert not RasaConversation.objects.filter(id=connection_id).exists()

    def test_author_delete_connection(self, conversation_db, user_client):
        user_client.force_login(conversation_db.author)
        connection = RasaConversation.objects.create(
            conversation=conversation_db, domain=TEST_DOMAIN
        )
        connection_id = connection.id
        response = user_client.get(
            conversation_db.get_absolute_url() + self.PATH + str(connection_id)
        )

        assert response.status_code == 302
        assert not RasaConversation.objects.filter(id=connection_id).exists()

    def test_try_other_user_delete_connection(self, conversation_db, user_client):
        connection = RasaConversation.objects.create(
            conversation=conversation_db, domain=TEST_DOMAIN
        )
        connection_id = connection.id
        with pytest.raises(Exception):
            user_client.get(
                conversation_db.get_absolute_url() + self.PATH + str(connection_id)
            )

    def test_try_unlogged_delete_connection(self, conversation_db, client):
        connection = RasaConversation.objects.create(
            conversation=conversation_db, domain=TEST_DOMAIN
        )
        connection_id = connection.id

        with pytest.raises(Exception):
            client.get(
                conversation_db.get_absolute_url() + self.PATH + str(connection_id)
            )
