from ej_integrations.utils import get_host_with_schema
from ej_conversations.mommy_recipes import ConversationRecipes
from unittest.mock import patch
import mock


class TestIntegrationsUtils(ConversationRecipes):
    def test_get_npm_version(self):
        from ej_integrations.utils import get_npm_tag

        tag = get_npm_tag()
        assert tag.status_code == 200

        json = tag.json()
        assert json["latest"] != ""

    @patch("ej_integrations.utils.get_npm_tag")
    def test_error_npm_version(self, get_npm_tag):
        from ej_integrations.utils import npm_version

        assert npm_version() == {"latest": "request failed"}

    def test_extracting_host_and_http_from_request(self):
        REQUEST_META = {"HTTP_X_FORWARDED_PROTO": "http", "HTTP_HOST": "ejplatform.local"}
        request = mock.Mock()
        request.META = REQUEST_META
        host = get_host_with_schema(request)
        assert host == "http://ejplatform.local"

    def test_extracting_host_and_https_from_request(self):
        REQUEST_META = {
            "HTTP_X_FORWARDED_PROTO": "https",
            "HTTP_HOST": "ejplatform.local2",
        }
        request = mock.Mock()
        request.META = REQUEST_META
        host = get_host_with_schema(request)
        assert host == "https://ejplatform.local2"

    def test_extracting_host_and_empty_schema_from_request(self):
        REQUEST_META = {"HTTP_X_FORWARDED_PROTO": "", "HTTP_HOST": "ejplatform.local"}
        request = mock.Mock()
        request.META = REQUEST_META
        host = get_host_with_schema(request)
        assert host == "http://ejplatform.local"
