import pytest
from ej_conversations.tools.table import Tools
from ej_boards.mommy_recipes import BoardRecipes


class TestTemplateGenerator(BoardRecipes):

    @pytest.fixture
    def tools(self, conversation_db):
        conversation = conversation_db
        return Tools(conversation)

    def test_list_tools(self, tools):
        list_of_tools = tools.list()
        assert len(list_of_tools) > 0
        assert type(list_of_tools) is list

    def test_get_tool_mailing(self, tools):
        mailing_tool = tools.get('Mailing campaign')
        assert mailing_tool
        assert mailing_tool["integration"] != ""
        assert mailing_tool["description"] != ""
        assert mailing_tool["link"] != ""

    def test_get_tool_rasa(self, tools):
        rasa_tool = tools.get('Rasa chatbot')
        assert rasa_tool
        assert rasa_tool["integration"] != ""
        assert rasa_tool["description"] != ""
        assert rasa_tool["link"] != ""

    def test_get_tool_conversation_component(self, tools):
        conversation_component_tool = tools.get('Conversation component')
        assert conversation_component_tool
        assert conversation_component_tool["integration"] != ""
        assert conversation_component_tool["description"] != ""
        assert conversation_component_tool["link"] != ""

    def test_raise_on_invalid_tool(self, tools):
        with pytest.raises(Exception):
            tools.get('xpto')
