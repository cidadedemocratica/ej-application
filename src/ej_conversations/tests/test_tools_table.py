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

    def test_get_tool(self, tools):
        mailing_tool = tools.get('Mailing campaign')
        assert mailing_tool
        assert mailing_tool["integration"] != ""
        assert mailing_tool["description"] != ""
        assert mailing_tool["link"] != ""

    def test_raise_on_invalid_tool(self, tools):
        with pytest.raises(Exception):
            tools.get('xpto')
