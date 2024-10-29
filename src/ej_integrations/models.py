from ckeditor.fields import RichTextField

from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from src.ej_integrations.utils import get_host_with_schema
from .constants import MAX_CONVERSATION_DOMAINS


class RasaConversation(models.Model):
    """
    Allows correlation between a conversation and an instance of rasa
    running on an external website
    """

    conversation = models.ForeignKey(
        "ej_conversations.Conversation",
        on_delete=models.CASCADE,
        related_name="rasa_conversations",
    )

    domain = models.URLField(
        _("Domain"),
        max_length=255,
        help_text=_("The domain that the rasa bot webchat is hosted."),
    )

    class Meta:
        unique_together = (("conversation", "domain"),)
        ordering = ["-id"]

    @property
    def reached_max_number_of_domains(self):
        try:
            num_domains = RasaConversation.objects.filter(
                conversation=self.conversation
            ).count()
            return num_domains >= MAX_CONVERSATION_DOMAINS
        except Exception:
            return False

    def clean(self):
        super().clean()
        if self.reached_max_number_of_domains:
            raise ValidationError(_("a conversation can have a maximum of five domains"))


class OpinionComponent(models.Model):
    """
    OpinionComponent controls the steps to generate the script and css to
    configure the EJ opinion web component
    """

    conversation = models.OneToOneField(
        "ej_conversations.Conversation", on_delete=models.CASCADE
    )
    final_voting_message = RichTextField()

    def get_upload_url(self, request, filename: str) -> str:
        """
        get_upload_url returns the absolute path to filename.
        :filename: any OpinionComponent field that is an Image.
        """
        upload = getattr(self, filename)
        if upload and upload.name:
            host = get_host_with_schema(request)
            return f"{host}{settings.MEDIA_URL}{upload.name}"
        return ""


class WebchatHelper:
    AVAILABLE_ENVIRONMENT_MAPPING = {
        "http://localhost:8000": "http://localhost:5006/?token=thisismysecret",
        "https://ejplatform.pencillabs.com.br": "https://rasadefaultdev.pencillabs.com.br/?token=thisismysecret",
        "https://www.ejplatform.org": "https://rasadefault.pencillabs.com.br/?token=thisismysecret",
        "https://www.ejparticipe.org": "https://rasadefault.pencillabs.com.br/?token=thisismysecret",
    }

    @staticmethod
    def get_rasa_domain(host):
        return WebchatHelper.AVAILABLE_ENVIRONMENT_MAPPING.get(host)
