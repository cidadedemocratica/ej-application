import pytest
from ej_conversations.mommy_recipes import ConversationRecipes

from ej_conversations.tools.forms import ConversationComponentForm
from ej_conversations.tools.routes import conversation_component

ConversationRecipes.update_globals(globals())

class TestConversationComponentForm:
    def test_conversation_component_valid_form(self):
        form = ConversationComponentForm({'authentication_type': "register", 'theme': "default"})
        assert form.is_valid()

class TestComponentConversationRoute(ConversationRecipes):
     def test_post_component_conversation_valid_form(self, db, mk_conversation, rf):
        conversation = mk_conversation()

        request = rf.post(
            conversation.get_absolute_url() + '/tools/component', {'authentication_type': "register", 'theme': "default"}
        )
        response = conversation_component(request, conversation, None)
        assert response['conversation_component'].get_props() == " authenticate-with=register"
        assert response['form'].is_valid()
        assert response['conversation'].id == conversation.id

     def test_post_votorantim_conversation_valid_form(self, db, mk_conversation, rf):
        conversation = mk_conversation()

        request = rf.post(
            conversation.get_absolute_url() + '/tools/rasa', {'authentication_type': "mautic", 'theme': "votorantim"}
        )
        response = conversation_component(request, conversation, None)
        assert response['conversation_component'].get_props() == 'theme=votorantim  authenticate-with=mautic'
        assert response['form'].is_valid()
        assert response['conversation'].id == conversation.id

     def test_post_icd_conversation_valid_form(self, db, mk_conversation, rf):
        conversation = mk_conversation()

        request = rf.post(
            conversation.get_absolute_url() + '/tools/rasa', {'authentication_type': "analytics", 'theme': "icd"}
        )
        response = conversation_component(request, conversation, None)
        assert response['conversation_component'].get_props() == 'theme=icd  authenticate-with=analytics'
        assert response['form'].is_valid()
        assert response['conversation'].id == conversation.id