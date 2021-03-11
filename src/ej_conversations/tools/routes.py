from boogie.router import Router
from .. import forms, models
from ..tools.utils import npm_version
from ..tools.table import Tools
from django.utils.translation import ugettext_lazy as _
from django.http import HttpResponse
from .utils import npm_version, generate_props
from .forms import ConversationComponentForm, AUTH_TOOLTIP_TEXTS, THEME_PALETTES

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
    schema = 'https' if settings.ENVIRONMENT != 'local' else 'http'
    form = ConversationComponentForm(request.POST)
    component_props = "authenticate-with=register"

    if request.method == 'POST':
        component_props = generate_props(form)
    tools = Tools(conversation)
    return {"schema": schema,
            "tool": tools.get(_('Conversation component')),
            "npm_version": npm_version(),
            "conversation": conversation,
            "form": form,
            "theme_palettes": THEME_PALETTES,
            "component_props": component_props,
    }
