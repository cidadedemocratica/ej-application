import mock
import pytest

from ej_conversations.models import ConversationManagerInvitation
from ej_conversations.tasks import send_manager_invitation_email


@pytest.fixture
def manager_invitation(conversation, mk_conversation_manager_invitation):
    manager = conversation.author.__class__.objects.create_user(
        "manager@example.com", "password", name="Manager"
    )
    return mk_conversation_manager_invitation(
        conversation,
        manager=manager,
        invited_by=conversation.author,
    )


def test_send_manager_invitation_email(db, manager_invitation):
    origin = "https://example.com"

    with mock.patch.object(
        ConversationManagerInvitation,
        "send_invitation",
    ) as send_invitation:
        send_manager_invitation_email(manager_invitation.id, origin)

    send_invitation.assert_called_once_with(origin)


def test_send_manager_invitation_email_task_name():
    assert (
        send_manager_invitation_email.name
        == "ej_conversations.tasks.send_manager_invitation_email"
    )


def test_send_manager_invitation_email_ignores_missing_invitation(db):
    send_manager_invitation_email(999999, "https://example.com")
