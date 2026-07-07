import pytest

from ej_users.models import User


@pytest.mark.parametrize("field", ["is_staff", "is_superuser"])
def test_can_access_dataviz_with_staff_or_superuser(db, conversation, field):
    user = User.objects.create_user("dataviz-user@server.com", "password")
    setattr(user, field, True)
    user.save()

    assert user.has_perm("ej.can_access_dataviz", conversation)


def test_can_access_dataviz_with_conversation_author(db, conversation):
    user = User.objects.create_user("dataviz-author@server.com", "password")
    conversation.author = user
    conversation.save()

    assert user.has_perm("ej.can_access_dataviz", conversation)


def test_can_access_dataviz_without_permission(db, conversation):
    user = User.objects.create_user("dataviz-user@server.com", "password")

    assert not user.has_perm("ej.can_access_dataviz", conversation)
