import pytest

from ej_users.models import User
from ej_boards.forms import BoardForm


@pytest.fixture
def user(db):
    user = User.objects.create_user('email@server.com', 'password')
    user.board_name = 'testboard'
    user.save()
    return user


class TestStereotypeForm:
    def test_init(self):
        BoardForm()

    def test_valid_data(self, user):
        form = BoardForm({
            'slug': "slug",
            'title': 'title',
            'description': "description",
            'palette': 'Grey'
        })
        assert form.is_valid()
        board = form.save(commit=False)
        board.owner = user
        board.save()
        assert board.title == "title"
        assert board.slug == "slug"
        assert board.description == "description"
        assert board.palette == "Grey"

    def test_blank_data(self, db):
        form = BoardForm({})
        assert not form.is_valid()
        assert form.errors == {
            'title': ['This field is required.'],
            'slug': ['This field is required.'],
            'palette': ['This field is required.'],
        }
