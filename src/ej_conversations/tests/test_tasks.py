import mock
import pytest
from django.core import mail

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
    accept_url = "https://example.com/boards/userboard/conversations/1/foo/members/token/accept/"
    manager_invitation.send_error = "previous failure"
    manager_invitation.save(update_fields=["send_error"])

    send_manager_invitation_email(manager_invitation.id, accept_url)

    manager_invitation.refresh_from_db()
    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == [manager_invitation.email]
    assert message.content_subtype == "html"
    assert "example.com" in message.body
    assert (
        f"<strong>{manager_invitation.conversation.title}</strong>"
        in message.body
    )
    assert f'<a href="{accept_url}">{accept_url}</a>' in message.body
    assert manager_invitation.sent_at is not None
    assert manager_invitation.send_error == ""


def test_send_manager_invitation_email_records_send_error(
    db, manager_invitation
):
    with mock.patch(
        "ej_conversations.tasks._dispatch_email",
        side_effect=Exception("smtp failed"),
    ):
        send_manager_invitation_email(
            manager_invitation.id,
            "https://example.com/invite/",
        )

    manager_invitation.refresh_from_db()
    assert len(mail.outbox) == 0
    assert manager_invitation.sent_at is None
    assert manager_invitation.send_error == "smtp failed"


def test_send_manager_invitation_email_ignores_missing_invitation(db):
    send_manager_invitation_email(999999, "https://example.com/invite/")

    assert len(mail.outbox) == 0
