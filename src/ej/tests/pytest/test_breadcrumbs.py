import pytest

from ej.breadcrumbs import get_breadcrumbs
from ej.jinja2 import breadcrumbs


@pytest.fixture
def rf():
    return pytest.importorskip("django.test").RequestFactory()


def assert_all_labels_are_present(items):
    assert all(item["label"] for item in items)


class TestGetBreadcrumbs:
    def test_empty_path_returns_empty_list(self, rf):
        request = rf.get("/")
        assert get_breadcrumbs(request) == []

    def test_unknown_app_returns_empty_list(self, rf):
        request = rf.get("/unknown/path/")
        assert get_breadcrumbs(request) == []

    def test_conversation_create_breadcrumb(self, rf):
        request = rf.get("/boards/minha-pauta/conversations/add/")
        result = get_breadcrumbs(request)

        assert len(result) == 3
        assert_all_labels_are_present(result)
        assert result[0]["url"] == "/profile/home/"
        assert result[1]["url"] == "/boards/minha-pauta/conversations/"
        assert result[2]["url"] is None

    def test_conversation_edit_breadcrumb(self, rf):
        request = rf.get(
            "/boards/minha-pauta/conversations/42/minha-conversa/edit/"
        )
        result = get_breadcrumbs(request)

        assert len(result) == 4
        assert_all_labels_are_present(result)
        assert result[0]["url"] == "/profile/home/"
        assert result[1]["url"] == "/boards/minha-pauta/conversations/"
        assert (
            result[2]["url"]
            == "/boards/minha-pauta/conversations/42/minha-conversa/"
        )
        assert result[3]["url"] is None

    def test_conversation_detail_breadcrumb_is_out_of_scope(self, rf):
        request = rf.get("/boards/minha-pauta/conversations/42/minha-conversa/")

        assert get_breadcrumbs(request) == []

    def test_conversation_moderate_breadcrumb_is_out_of_scope(self, rf):
        request = rf.get(
            "/boards/minha-pauta/conversations/42/minha-conversa/moderate/"
        )

        assert get_breadcrumbs(request) == []


class TestJinja2Breadcrumbs:
    def test_no_request_in_context(self):
        ctx = {}
        assert breadcrumbs(ctx) == []

    def test_delegates_to_get_breadcrumbs(self, rf):
        request = rf.get("/boards/minha-pauta/conversations/add/")
        ctx = {"request": request}

        assert breadcrumbs(ctx) == get_breadcrumbs(request)
