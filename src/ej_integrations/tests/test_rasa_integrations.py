import pytest
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from ej_users.models import User
from django.db import IntegrityError
from django.utils.translation import gettext as _
from django.test.client import Client
from ej_conversations.mommy_recipes import ConversationRecipes
from ej_integrations.models import RasaConversation, WebchatHelper
from ej_integrations.forms import RasaConversationForm
from ej_integrations.tests import HTTP_HOST, TEST_DOMAIN

ConversationRecipes.update_globals(globals())


class TestRasaConversation(ConversationRecipes):
    def test_creation_rasa_conversation(self, db, mk_conversation):
        conversation = mk_conversation()
        rasa_conversation = RasaConversation.objects.create(
            conversation=conversation, domain=TEST_DOMAIN
        )
        assert rasa_conversation.id is not None

    def test_creation_duplicated_rasa_conversation(self, db, mk_conversation):
        conversation = mk_conversation()
        rasa_conversation = RasaConversation.objects.create(
            conversation=conversation, domain=TEST_DOMAIN
        )
        assert rasa_conversation.id is not None
        with pytest.raises(IntegrityError):
            RasaConversation.objects.create(conversation=conversation, domain=TEST_DOMAIN)


class TestRasaConversationForm(ConversationRecipes):
    def test_rasa_conversation_valid_form(self, db, mk_conversation):
        conversation = mk_conversation()
        form = RasaConversationForm(
            {"domain": "http://another.com", "conversation": conversation.id}
        )
        assert form.is_valid()

    def test_rasa_conversation_invalid_form(self, db, mk_conversation):
        mk_conversation()
        form = RasaConversationForm({"domain": "notadomain"})
        assert not form.is_valid()
        assert _("Enter a valid URL.") == form.errors["domain"][0]

    def test_rasa_conversation_form_exists(self, db, mk_conversation):
        conversation = mk_conversation()
        RasaConversation.objects.create(conversation=conversation, domain=TEST_DOMAIN)
        form = RasaConversationForm(
            {"domain": TEST_DOMAIN, "conversation": conversation.id}
        )
        assert not form.is_valid()
        assert (
            _("Rasa conversation with this Conversation and Domain already exists.")
            == form.errors["domain"][0]
        )

    def test_rasa_conversation_form_domain_already_in_use(
        self, db, mk_conversation, mk_user
    ):
        conversation1 = mk_conversation()
        user = mk_user(email="test@domain.com")
        conversation2 = mk_conversation(author=user)
        RasaConversation.objects.create(conversation=conversation1, domain=TEST_DOMAIN)
        form = RasaConversationForm(
            {"domain": TEST_DOMAIN, "conversation": conversation2.id}
        )
        assert (
            _("Site already integrated with conversation Conversation, try another url.")
            == form.errors["domain"][0]
        )

    def test_rasa_conversation_invalid_number_of_domains(self, db, mk_conversation):
        conversation = mk_conversation()
        RasaConversation.objects.create(
            conversation=conversation, domain="https://domain1.com.br/"
        )
        RasaConversation.objects.create(
            conversation=conversation, domain="https://domain2.com.br/"
        )
        RasaConversation.objects.create(
            conversation=conversation, domain="https://domain3.com.br/"
        )
        RasaConversation.objects.create(
            conversation=conversation, domain="https://domain4.com.br/"
        )
        RasaConversation.objects.create(
            conversation=conversation, domain="https://domain5.com.br/"
        )
        form = RasaConversationForm(
            {"domain": "https://domain6.com.br/", "conversation": conversation.id}
        )
        assert not form.is_valid()
        assert (
            _("a conversation can have a maximum of five domains")
            == form.errors["__all__"][0]
        )


class TestRasaConversationFormRoute(ConversationRecipes):
    def test_post_rasa_conversation_valid_form(self, db, mk_conversation):
        conversation = mk_conversation()

        client = Client()
        admin = User.objects.create_superuser("myemail@test.com", "password")
        client.force_login(user=admin)
        response = client.post(
            conversation.get_absolute_url() + "tools/chatbot/webchat",
            {"conversation": conversation.id, "domain": TEST_DOMAIN},
            HTTP_HOST=HTTP_HOST,
        )

        assert response.status_code == 200
        assert RasaConversation.objects.filter(
            conversation=conversation, domain=TEST_DOMAIN
        ).exists()

    def test_post_rasa_conversation_invalid_form(self, conversation_db):
        conversation = conversation_db
        client = Client()
        admin = User.objects.create_superuser("myemail@test.com", "password")
        client.force_login(user=admin)
        invalid_domain = "nope"
        tool_url = conversation_db.patch_url("conversation-tools:webchat")
        response = client.post(
            tool_url,
            {"conversation": conversation.id, "domain": invalid_domain},
            HTTP_HOST=HTTP_HOST,
        )
        response_content = response.content.decode("utf-8")
        assert _("Enter a valid URL") in response_content
        assert not RasaConversation.objects.filter(
            conversation=conversation, domain=invalid_domain
        ).exists()

    def test_access_to_rasa_conversation_invalid_permission_form(
        self, rf, user_client, conversation_db
    ):
        response = user_client.get(
            conversation_db.get_absolute_url() + "tools/chatbot/webchat"
        )

        assert response.status_code == 302
        assert response.url == "/login/"


class TestRasaConversationIntegrationsAPI(ConversationRecipes):
    BASE_URL = "/api/v1"

    def test_conversations_endpoint(self, db, mk_conversation):
        conversation = mk_conversation()
        TEST_DOMAIN = "https://domain.com.br"

        RasaConversation.objects.create(conversation=conversation, domain=TEST_DOMAIN)
        path = self.BASE_URL + f"/rasa-conversations/integrations/?domain={TEST_DOMAIN}"

        user = User.objects.create_user("email2@server.com", "password")
        token = Token.objects.create(user=user)
        api = APIClient()
        api.credentials(HTTP_AUTHORIZATION="Token " + token.key)
        response = api.get(path)

        assert response.status_code == 200
        assert conversation.text == response.data.get("conversation").get("text")
        assert conversation.id == response.data.get("conversation").get("id")
        assert TEST_DOMAIN == response.data.get("domain")

    def test_no_integration_api(self, db):
        url = self.BASE_URL + f"/rasa-conversations/integrations/?domain={TEST_DOMAIN}"

        user = User.objects.create_user("email2@server.com", "password")
        token = Token.objects.create(user=user)
        api = APIClient()
        api.credentials(HTTP_AUTHORIZATION="Token " + token.key)
        response = api.get(url)
        assert response.status_code == 200
        assert response.data == {}


class TestWebchatHelper:
    def setup_method(self, method):
        self.environments = {
            "local": "http://localhost:8000",
            "dev": "https://ejplatform.pencillabs.com.br",
            "prod": "https://www.ejplatform.org",
        }

    def test_local_webchat_integration(self):
        rasa_environment = WebchatHelper.get_rasa_domain(self.environments["local"])
        assert rasa_environment

    def test_dev_webchat_integration(self):
        rasa_environment = WebchatHelper.get_rasa_domain(self.environments["dev"])
        assert rasa_environment

    def test_prod_webchat_integration(self):
        rasa_environment = WebchatHelper.get_rasa_domain(self.environments["prod"])
        assert rasa_environment

    def test_if_instance_not_available(self):
        rasa_environment = WebchatHelper.get_rasa_domain(HTTP_HOST)
        assert not rasa_environment
