from celery import shared_task

from ej.celery import app as celery_app
from ej_conversations.models import ConversationManagerInvitation

logger = celery_app.log.get_default_logger()


@shared_task
def send_manager_invitation_email(invitation_id, origin):
    invitation = (
        ConversationManagerInvitation.objects.select_related(
            "conversation",
            "conversation__board",
            "invited_by",
            "user",
        )
        .filter(id=invitation_id)
        .first()
    )
    if invitation is None:
        logger.info(
            "Task: manager invitation %s does not exist.", invitation_id
        )
        return

    invitation.send_invitation(origin)
