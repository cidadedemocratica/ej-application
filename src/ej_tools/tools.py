from django.utils.translation import gettext_lazy as _
from django.core.exceptions import PermissionDenied
from rest_framework.authtoken.models import Token
from django.shortcuts import reverse


class AbstractTool:
    def __init__(self, **kwargs):
        self.name: str = ""
        self.description: str = ""
        self.link: str = ""
        self.about: str = ""
        self.is_active: bool = False

    def raise_error_if_not_active(self):
        if self.is_active:
            return
        raise PermissionDenied()


class BotsWebchatTool(AbstractTool):
    def __init__(self, is_active=True, **kwargs):
        AbstractTool.__init__(self)
        self.name: str = "Webchat"
        self.description: str = _(
            "Integrate this conversation with a web client, called a webchat."
            + "Create a chat on your website page."
        )
        self.share: str = _(
            "I am the virtual assistant for the EJ platform. Empurrando Juntos, or EJ Platform,"
            + "is an opinion consultation platform focused on States and Organizations."
            + "We would like your participation in the following discussion:"
        )
        self.is_active = is_active


class BotsTelegramTool(AbstractTool):
    def __init__(self, is_active=True, **kwargs):
        AbstractTool.__init__(self)
        self.name: str = "Telegram"
        self.description: str = _(
            "Telegram user will interact with the bot in the private chat. "
            + "Use telegram API for connection."
        )
        self.share: str = _(
            "I am the virtual assistant for the EJ platform. Empurrando Juntos, or EJ Platform,"
            + "is an opinion consultation platform focused on States and Organizations."
            + "We would like your participation in the following discussion:"
        )
        self.options = [
            ("Duda", _("DudaEjBot")),
            ("Boca De Lobo", _("BocaDeLoboBot")),
        ]
        self.is_active = is_active


class BotsWhatsappTool(AbstractTool):
    def __init__(self, is_active=True, **kwargs):
        AbstractTool.__init__(self)
        self.name: str = "WhatsApp"
        self.description: str = _(
            "Whatsapp user will interact with the bot in the private chat."
            + "Use Twilio as a broker for connection."
        )
        self.share: str = _(
            "I am the virtual assistant for the EJ platform. Empurrando Juntos, or EJ Platform, "
            + "is an opinion consultation platform focused on the State and Organizations. "
            + "We would like your participation in the following discussion:"
        )
        self.options = [
            ("Duda", "614567"),
            ("Boca de Lobo", "611234"),
        ]
        self.is_active = True


class MauticTool(AbstractTool):
    def __init__(self, conversation, is_active=True):
        AbstractTool.__init__(self)
        self.name: str = _("Mautic")
        self.description: str = _(
            "Integrate this conversation with the Mautic platform API, "
            + "allowing users who participate in this conversation to be automatically "
            + "synchronized with Mautic's contact base."
        )
        self.link: str = conversation.patch_url("conversation-tools:mautic")
        self.about: str = "/docs/?page=user-docs/tools-mautic.html"
        self.is_active: bool = is_active


class BotsTool(AbstractTool):
    def __init__(self, conversation, is_active=True, exclude=[]):
        AbstractTool.__init__(self)
        self.name: str = _("Opinion Bots")
        self.description: str = _(
            "Collect opinions using EJ's bots. You can collect on Whatsapp, Telegram and web pages."
        )
        self.link: str = conversation.patch_url("conversation-tools:chatbot")
        self.telegram = BotsTelegramTool()
        self.whatsapp = BotsWhatsappTool()
        self.webchat = BotsWebchatTool()
        self.child_tools = {
            "whatsapp": self.whatsapp,
            "telegram": self.telegram,
            "webchat": self.webchat,
        }
        self.is_active = is_active
        self.activate_child_tools(exclude)

    def activate_child_tools(self, excluded_tools):
        """TODO: Docstring for exclude_child_tools.

        :arg1: TODO
        :returns: TODO

        """
        for excluded_tool in excluded_tools:
            tool = self.child_tools[excluded_tool]
            tool.is_active = False


class OpinionComponentTool(AbstractTool):
    def __init__(self, conversation, is_active=True):
        AbstractTool.__init__(self)
        self.name: str = _("Opinion component")
        self.description: str = _(
            "Conduct opinion collections without your audience having to access EJ directly. "
            + "Allows you to vote, comment and view groups directly on html pages, "
            + "without impacting the experience of those who already access their networks and platforms."
        )
        self.link: str = conversation.patch_url("conversation-tools:opinion-component")
        self.about: str = "/docs/?page=user-docs/tools-opinion-component.html"
        self.is_active = is_active

    def get_preview_token(self, request, conversation):
        author_token = None
        if request.user.is_authenticated and request.user.id == conversation.author.id:
            try:
                author_token = Token.objects.get(user=conversation.author)
            except Exception as e:
                author_token = Token.objects.create(user=conversation.author)
        return author_token


class RocketChat(AbstractTool):
    def __init__(self, conversation, is_active=True):
        AbstractTool.__init__(self)
        self.name: str = _("Rocket.Chat")
        self.description: str = _(
            "Rocket.Chat instance for segmented communication with conversation participants."
        )
        self.link: str = reverse(
            "dataviz:communication", kwargs={"conversation": conversation, "slug": conversation.slug}
        )
        self.about: str = "/docs/user-guides/pt-br/tools-chatbot.html#rocket-chat"
        self.is_active = is_active


class MailingTool(AbstractTool):
    MAILING_TOOL_CHOICES = (
        ("mautic", _("Mautic")),
        ("mailchimp", _("MailChimp")),
    )

    MAILING_TOOLTIP_TEXTS = {
        "mailchimp": _("Mailchimp campaign"),
        "mautic": _("Uses a mautic campaign "),
    }

    def __init__(self, conversation, is_active=True):
        AbstractTool.__init__(self)
        self.name: str = _("Mailing campaign")
        self.description: str = _(
            "Generates a html template of this conversation, for mailing marketing campaigns."
        )
        self.link: str = conversation.patch_url("conversation-tools:mailing")
        self.about: str = "/docs/?page=user-docs/tools-mail-template.html"
        self.is_active = is_active


class Tools:
    """
    Tools is an utility class to manage EJ tools;
    """

    @staticmethod
    def get(tool_name, tools):
        tool = list(filter(lambda tool: tool.name == tool_name, tools))
        if len(tool) == 0 or len(tool) > 1:
            raise Exception("tool not found")
        return tool[0]
