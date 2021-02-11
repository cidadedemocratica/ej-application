import pytest
from requests import get
from ej_conversations.mommy_recipes import ConversationRecipes
from unittest.mock import patch


class TestIntegrationsUtils(ConversationRecipes):
    def test_get_npm_version(self):
        from ej_conversations.tools.utils import get_npm_tag
        tag = get_npm_tag()
        assert tag.status_code == 200

        json = tag.json()
        assert json['latest'] != ''

    @patch('ej_conversations.tools.utils.get_npm_tag')
    def test_error_npm_version(self, get_npm_tag):
        from ej_conversations.tools.utils import npm_version
        assert npm_version() == {"latest": "request failed"}
