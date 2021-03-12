import pytest
from django.db import IntegrityError
from django.utils.translation import ugettext as _
from django.test import TestCase

from ej_conversations.mommy_recipes import ConversationRecipes
from ej_conversations.models import RasaConversation
from ej_conversations.tools.forms import RasaConversationForm
from ej_conversations.tools.routes import rasa

ConversationRecipes.update_globals(globals())

class TestRasaConversation(ConversationRecipes):
    def test_creation_rasa_conversation(self, db, mk_conversation):
        conversation = mk_conversation()
        rasa_conversation = RasaConversation.objects.create(conversation=conversation, domain="https://domain.com.br")
        assert rasa_conversation.id is not None

    def test_creation_duplicated_rasa_conversation(self, db, mk_conversation):
        conversation = mk_conversation()
        rasa_conversation = RasaConversation.objects.create(conversation=conversation, domain="https://domain.com.br")
        assert rasa_conversation.id is not None
        with pytest.raises(IntegrityError):
            RasaConversation.objects.create(conversation=conversation, domain="https://domain.com.br")

class TestRasaConversationForm(ConversationRecipes):
    def test_rasa_conversation_valid_form(self, db, mk_conversation):
        conversation = mk_conversation()
        form = RasaConversationForm({'domain': "http://another.com", 'conversation': conversation.id}, conversation=conversation)
        print(form)
        assert form.is_valid()

    def test_rasa_conversation_invalid_form(self, db, mk_conversation):
        conversation = mk_conversation()
        form = RasaConversationForm({'domain': "notadomain"}, conversation=conversation)
        assert not form.is_valid()
        assert _("Enter a valid URL.") == form.errors["domain"][0]

    def test_rasa_conversation_form_exists(self, db, mk_conversation):
        conversation = mk_conversation()
        RasaConversation.objects.create(conversation=conversation, domain="https://domain.com.br")
        form = RasaConversationForm({'domain': "https://domain.com.br", 'conversation': conversation.id}, conversation=conversation)
        assert not form.is_valid()
        print(form.errors.keys())
        assert _("Rasa conversation with this Conversation and Domain already exists.") == form.errors['__all__'][0]

class TestRasaConversationFormRoute(ConversationRecipes):
     def test_post_rasa_conversation_valid_form(self, db, mk_conversation, rf):
        conversation = mk_conversation()

        request = rf.post(
            conversation.get_absolute_url() + '/tools/rasa', {"conversation": conversation.id, "domain": "http://domain.com.br"}
        )
        response = rasa(request, conversation, None)
        assert response['connections']
        assert response['connections'][0].domain == "http://domain.com.br"
        assert response['connections'][0].conversation.id == conversation.id

     def test_post_rasa_conversation_invvalid_form(self, db, mk_conversation, rf):
        conversation = mk_conversation()

        request = rf.post(
            conversation.get_absolute_url() + '/tools/rasa', {"conversation": conversation.id, "domain": "nope"}
        )
        response = rasa(request, conversation, None)
        assert not response['connections']
        assert not response['form'].is_valid()