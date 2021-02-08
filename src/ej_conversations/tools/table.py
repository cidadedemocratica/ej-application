from django.utils.translation import ugettext_lazy as _


class Tools():

    def __init__(self, conversation):
        self.conversation = conversation

    def list(self):
        return [{
            "integration": _("Mailing campaign"),
            "description": _("Generates a html template of this conversation, for mailing marketing campaigns."),
            "link": self.conversation.url('conversation:mailing'),
        },
            {
            "integration": _("Conversation component"),
            "description": _("Adds EJ directly to your site. Enables voting, commenting, and clusters visualization directly on a html page."),
            "link": ""
        }
        ]

    def get(self, name):
        tools = self.list()
        selected_tool = {}
        for tool in tools:
            if(tool["integration"] == name):
                selected_tool = tool
                break
            if(not selected_tool):
                raise Exception("tool not found")
        return selected_tool

