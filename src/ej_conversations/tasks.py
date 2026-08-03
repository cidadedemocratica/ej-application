from urllib.parse import urlparse

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import get_template
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from ej.celery import app as celery_app
from ej_conversations.models import ConversationManagerInvitation

logger = celery_app.log.get_default_logger()


def _display_name(user, fallback):
    if user is None:
        return fallback

    return getattr(user, "name", "") or getattr(user, "email", "") or fallback


def _from_email():
    from_email = settings.DEFAULT_FROM_EMAIL
    if settings.DEFAULT_FROM_NAME:
        from_email = f"{settings.DEFAULT_FROM_NAME} <{from_email}>"
    return from_email


def _dispatch_email(invitation: ConversationManagerInvitation, accept_url: str):
    inviter_name = _display_name(
        invitation.invited_by, invitation.invited_by.email
    )
    invitee_name = _display_name(invitation.user, invitation.email)
    site_domain = urlparse(accept_url).netloc
    context = {
        "accept_url": accept_url,
        "conversation_title": invitation.conversation.title,
        "invitee_email": invitation.email,
        "invitee_name": invitee_name,
        "inviter_name": inviter_name,
        "name_of_granter": inviter_name,
        "person_name": invitee_name,
        "site_domain": site_domain,
    }
    subject = _("%(inviter)s shared access to an EJ conversation") % {
        "inviter": inviter_name
    }
    template = get_template(
        "ej_conversations/manager-invitation-message.jinja2"
    )
    message = template.render(context)
    email = EmailMessage(
        subject=subject,
        body=message,
        from_email=_from_email(),
        to=[invitation.email],
    )
    email.content_subtype = "html"
    email.send()


@shared_task
def send_manager_invitation_email(invitation_id, accept_url):
    invitation = (
        ConversationManagerInvitation.objects.select_related(
            "conversation",
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

    try:
        _dispatch_email(invitation, accept_url)
    except Exception as exc:
        invitation.send_error = str(exc)
        invitation.save(update_fields=["send_error"])
        logger.exception(
            "Task: error sending manager invitation %s.", invitation.id
        )
        return

    invitation.sent_at = timezone.now()
    invitation.send_error = ""
    invitation.save(update_fields=["sent_at", "send_error"])
