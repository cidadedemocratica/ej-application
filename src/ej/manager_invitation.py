import uuid
from logging import getLogger
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.db import models, transaction
from django.db.models.functions import Lower
from django.template.loader import get_template
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from model_utils.models import TimeStampedModel

logger = getLogger("ej")


class ManagerInvitationQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def pending(self):
        return self.active().filter(
            status=AbstractManagerInvitation.Status.PENDING
        )


class AbstractManagerInvitation(TimeStampedModel):
    email_subject_template = None
    email_template_name = None

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        ACCEPTED = "accepted", _("Accepted")

    email = models.EmailField()
    accept_token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
    )
    is_active = models.BooleanField(default=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    send_error = models.TextField(blank=True)

    objects = ManagerInvitationQuerySet.as_manager()

    class Meta:
        abstract = True

    @staticmethod
    def normalize_email(email):
        return (email or "").strip().lower()

    def matches_user_email(self, user):
        user_email = self.normalize_email(user.email)
        invitation_email = self.normalize_email(self.email)
        return user_email == invitation_email

    def save(self, *args, **kwargs):
        self.email = self.normalize_email(self.email)
        super().save(*args, **kwargs)
        if not self.is_active or self.status != self.Status.ACCEPTED:
            self.get_manager_model().objects.filter(invitation=self).delete()

    def resolve_user(self):
        """Return the invited user, using the linked user first and email fallback."""
        if self.user_id:
            return self.user

        email = self.normalize_email(self.email)
        if not email:
            return None

        return (
            get_user_model()
            .objects.annotate(normalized_email=Lower("email"))
            .filter(normalized_email=email)
            .first()
        )

    def get_manager_model(self):
        raise NotImplementedError

    def get_manager_lookup(self, user):
        raise NotImplementedError

    def get_accept_url(self, origin):
        raise NotImplementedError

    def get_email_context(self):
        raise NotImplementedError

    def send_invitation(self, origin):
        if not self.is_active or self.status != self.Status.PENDING:
            return

        try:
            inviter_name = _display_name(self.invited_by, self.invited_by.email)
            invitee_name = _display_name(self.user, self.email)
            accept_url = self.get_accept_url(origin)
            context = {
                "accept_url": accept_url,
                "invitee_email": self.email,
                "invitee_name": invitee_name,
                "inviter_name": inviter_name,
                "name_of_granter": inviter_name,
                "person_name": invitee_name,
                "site_domain": urlparse(accept_url).netloc,
                **self.get_email_context(),
            }
            message = get_template(self.email_template_name).render(context)
            email = EmailMessage(
                subject=self.email_subject_template % {"inviter": inviter_name},
                body=message,
                from_email=_from_email(),
                to=[self.email],
            )
            email.content_subtype = "html"
            email.send()
        except Exception as exc:
            self.send_error = str(exc)
            self.save(update_fields=["send_error"])
            logger.exception(
                "Error sending %s %s.",
                self._meta.verbose_name,
                self.id,
            )
            return

        self.sent_at = timezone.now()
        self.send_error = ""
        self.save(update_fields=["sent_at", "send_error"])

    def sync_manager(self):
        """Create or update manager membership when this invitation is accepted."""
        user = self.resolve_user()
        is_accepted = (
            self.status == self.Status.ACCEPTED
            and self.is_active
            and user is not None
        )
        if not is_accepted:
            return None

        manager_model = self.get_manager_model()
        manager, created = manager_model.objects.get_or_create(
            **self.get_manager_lookup(user),
            defaults={"invitation": self},
        )
        if not created and manager.invitation_id != self.id:
            previous_invitation = manager.invitation
            manager.invitation = self
            manager.save(update_fields=["invitation"])
            if previous_invitation and previous_invitation.is_active:
                previous_invitation.is_active = False
                previous_invitation.save(update_fields=["is_active"])

        return manager

    def delete_manager(self):
        """Delete manager membership and invalidate this invitation."""
        self.get_manager_model().objects.filter(invitation=self).delete()
        if self.is_active:
            self.is_active = False
            self.save(update_fields=["is_active"])

    def accept(self, user=None):
        """Accept this invitation and ensure manager membership exists."""
        # Serialize acceptance so a token cannot grant access more than once.
        with transaction.atomic():
            invitation = type(self).objects.select_for_update().get(pk=self.pk)
            if not invitation.is_active:
                raise ValidationError(
                    _("Inactive invitations cannot be accepted.")
                )
            if invitation.status != self.Status.PENDING:
                raise ValidationError(
                    _("Only pending invitations can be accepted.")
                )

            update_fields = ["status"]
            if user is not None and invitation.user_id != user.id:
                invitation.user = user
                update_fields.append("user")
            invitation.status = invitation.Status.ACCEPTED
            invitation.save(update_fields=update_fields)
            invitation.sync_manager()
            self.status = invitation.status
            self.user_id = invitation.user_id
        return invitation


def _display_name(user, fallback):
    if user is None:
        return fallback

    return getattr(user, "name", "") or getattr(user, "email", "") or fallback


def _from_email():
    from_email = settings.DEFAULT_FROM_EMAIL
    if settings.DEFAULT_FROM_NAME:
        from_email = f"{settings.DEFAULT_FROM_NAME} <{from_email}>"
    return from_email
