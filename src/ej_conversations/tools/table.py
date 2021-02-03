from django.utils.translation import ugettext_lazy as _


class Tools():

    def __init__(self, conversation):
        self.conversation = conversation

    def get(self):
        return [{
            "integration": _("Mailing campaign"),
            "description": _("Generates a html template of this conversation, for mailing marketing campaigns."),
            "link": self.conversation.url('conversation:mailing')
        },
            {
            "integration": _("Conversation component"),
            "description": _("Adds EJ directly to your site. Enables voting, commenting, and clusters visualization directly on a html page."),
            "link": ""
        }
        ]
