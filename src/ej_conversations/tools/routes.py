from boogie.router import Router
from .. import forms, models
from ..tools.utils import npm_version
from ..tools.table import Tools
from django.utils.translation import ugettext_lazy as _
from django.http import HttpResponse
from .utils import npm_version

app_name = "ej_conversations_tools"
urlpatterns = Router(
    template="ej_conversations_tools/{name}.jinja2", models={"conversation": models.Conversation}
)
conversation_tools_url = f"conversations/<model:conversation>/<slug:slug>/tools"


@urlpatterns.route(conversation_tools_url)
def index(request, conversation, slug, npm=npm_version):
    tools = Tools(conversation)
    return {
        "tools": tools.list(),
        "conversation": conversation
    }


@urlpatterns.route(conversation_tools_url + "/mailing")
def mailing(request, conversation, slug):
    from .mailing import TemplateGenerator
    if request.method == "POST":
        generator = TemplateGenerator(conversation, request, "mautic")
        template = generator.get_template()
        response = HttpResponse(template, content_type="text/html")
        response['Content-Disposition'] = 'attachment; filename=template.html'
        return response

    tools = Tools(conversation)
    return {"conversation": conversation, "tool": tools.get(_('Mailing campaign'))}


@urlpatterns.route(conversation_tools_url + "/component")
def conversation_component(request, conversation, slug):
    from django.conf import settings

    tools = Tools(conversation)
    schema = 'https' if settings.ENVIRONMENT != 'local' else 'http'
    return {"schema": schema,
            "tool": tools.get(_('Conversation component')),
            "npm_version": npm_version(),
            "conversation": conversation
            }
