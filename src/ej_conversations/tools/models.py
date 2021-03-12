from django.utils.translation import ugettext_lazy as _
from boogie import models


class RasaConversation(models.Model):
    """
    Allows correlation between a conversation and an instance of rasa
    running on an external website
    """

    conversation = models.ForeignKey("Conversation", on_delete=models.CASCADE, related_name="rasa_conversations")
    domain = models.URLField(
        _("Domain"),
        max_length=255,
        help_text=_("The domain that the rasa bot webchat is hosted."),)

    class Meta:
        unique_together = (('conversation', 'domain'),)
