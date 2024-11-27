import json
from typing import Any, Dict
from django.shortcuts import render, redirect
from django.utils.decorators import method_decorator
from django.views.generic import UpdateView
from django.http import HttpResponse
from .forms import (
    RasaConversationForm,
    MailingToolForm,
    OpinionComponentForm,
)
from .models import (
    OpinionComponent,
    RasaConversation,
    WebchatHelper,
)
from ej_conversations.models import Conversation
from ej.decorators import can_access_tool_page, can_edit_conversation
from .utils import (
    npm_version,
    user_can_add_new_domain,
    get_host_with_schema,
)
from ej_integrations.tools import (
    MailingTool,
    BotsTool,
    OpinionComponentTool,
    BotsWebchatTool,
    BotsWhatsappTool,
    BotsTelegramTool,
)


@can_edit_conversation
def index(request, board_slug, conversation_id, slug):
    conversation = Conversation.objects.get(id=conversation_id)
    tools = [
        MailingTool(conversation),
        OpinionComponentTool(conversation),
        BotsTool(conversation, exclude=["whatsapp"]),
    ]
    context = {"tools": tools, "conversation": conversation, "current_page": "tools"}
    return render(request, "ej_integrations/index.jinja2", context)


@can_access_tool_page
def mailing(request, board_slug, conversation_id, slug):
    from .mailing import TemplateGenerator

    conversation = Conversation.objects.get(id=conversation_id)
    template = "null"
    form = MailingToolForm(request.POST, conversation_id=conversation)
    if request.method == "POST" and form.is_valid():
        form_data = form.cleaned_data
        generator = TemplateGenerator(conversation, request, form_data)
        template = generator.get_template()
        if "download" in request.POST:
            response = HttpResponse(template, content_type="text/html")
            response["Content-Disposition"] = "attachment; filename=template.html"
            return response
        if "preview" in request.POST:
            template = json.dumps(template, ensure_ascii=False)
    context = {
        "conversation": conversation,
        "tool": MailingTool(conversation),
        "template_preview": template,
        "form": form,
    }
    return render(request, "ej_integrations/mailing.jinja2", context)


@method_decorator(can_access_tool_page, name="dispatch")
class OpinionComponentView(UpdateView):
    template_name = "ej_integrations/opinion-component.jinja2"
    model = OpinionComponent

    def get_object(self, queryset=None):
        try:
            opinion_component = OpinionComponent.objects.get(
                conversation=self.conversation
            )
        except OpinionComponent.DoesNotExist:
            opinion_component = None
        return opinion_component

    def get(self, request, *args, **kwargs):
        conversation_id = self.kwargs.get("conversation_id", None)
        self.conversation = Conversation.objects.get(id=conversation_id)

        opinion_component = self.get_object()
        self.opinion_component_form = OpinionComponentForm(
            initial={"conversation": self.conversation}, instance=opinion_component
        )
        return render(request, self.template_name, self.get_context_data(**kwargs))

    def post(self, request, *args, **kwargs):
        conversation_id = self.kwargs.get("conversation_id", None)
        self.conversation = Conversation.objects.get(id=conversation_id)
        if "custom" in request.POST:
            opinion_component = self.get_object()
            self.opinion_component_form = OpinionComponentForm(
                request.POST, request.FILES, instance=opinion_component
            )
            if self.opinion_component_form.is_valid():
                self.opinion_component_form.save()
            else:
                return render(
                    request, self.template_name, self.get_context_data(**kwargs)
                )

        return redirect(
            self.conversation.patch_url("conversation-tools:opinion-component-preview")
        )

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        return {
            "ej_domain": get_host_with_schema(self.request),
            "tool": OpinionComponentTool(self.conversation),
            "npm_version": npm_version(),
            "conversation": self.conversation,
            "opinion_component_form": self.opinion_component_form,
        }


def opinion_component_preview(request, board_slug, conversation_id, slug):
    host = get_host_with_schema(request)

    conversation = Conversation.objects.get(id=conversation_id)
    tool = OpinionComponentTool(conversation)
    preview_token = tool.get_preview_token(request, conversation)
    tool.raise_error_if_not_active()
    theme = request.GET.get("theme", "icd")
    context = {
        "conversation": conversation,
        "theme": theme,
        "host": host,
        "conversation_author_token": preview_token,
    }
    return render(request, "ej_integrations/opinion-component-preview.jinja2", context)


@can_access_tool_page
def chatbot(request, board_slug, conversation_id, slug):
    conversation = Conversation.objects.get(id=conversation_id)
    context = {"conversation": conversation, "tool": BotsTool(conversation)}
    return render(request, "ej_integrations/chatbot.jinja2", context)


@can_access_tool_page
def telegram(request, board_slug, conversation_id, slug):
    conversation = Conversation.objects.get(id=conversation_id)
    context = {"conversation": conversation, "tool": BotsTelegramTool(conversation)}
    return render(request, "ej_integrations/telegram.jinja2", context)


@can_access_tool_page
def whatsapp(request, board_slug, conversation_id, slug):
    conversation = Conversation.objects.get(id=conversation_id)
    context = {"conversation": conversation, "tool": BotsWhatsappTool(conversation)}
    return render(request, "ej_integrations/whatsapp.jinja2", context)


@can_access_tool_page
def webchat(request, board_slug, conversation_id, slug):
    conversation = Conversation.objects.get(id=conversation_id)

    user_can_add = user_can_add_new_domain(request.user, conversation)
    host = get_host_with_schema(request)
    webchat_preview_url = host + conversation.patch_url(
        "conversation-tools:webchat-preview"
    )

    if "webchat-preview" in request.POST:
        RasaConversation.objects.get_or_create(
            conversation=conversation, domain=webchat_preview_url
        )
        return redirect(conversation.patch_url("conversation-tools:webchat-preview"))

    if request.method == "POST":
        form = RasaConversationForm(request.POST)
        if not user_can_add:
            raise PermissionError(
                "user is not allowed to create conversation rasa connections"
            )
        if form.is_valid():
            form.save()
            form = RasaConversationForm()
    else:
        form = RasaConversationForm()

    conversation_rasa_connections = RasaConversation.objects.filter(
        conversation=conversation
    )
    context = {
        "conversation": conversation,
        "conversation_rasa_connections": conversation_rasa_connections,
        "tool": BotsWebchatTool(conversation),
        "form": form,
        "is_valid_user": user_can_add,
        "webchat_preview_url": webchat_preview_url,
    }
    return render(request, "ej_integrations/webchat.jinja2", context)


def webchat_preview(request, board_slug, conversation_id, slug):
    conversation = Conversation.objects.get(id=conversation_id)

    host = get_host_with_schema(request)
    rasa_domain = WebchatHelper.get_rasa_domain(host)
    context = {"conversation": conversation, "rasa_domain": rasa_domain}
    return render(request, "ej_integrations/webchat-preview.jinja2", context)


def delete_connection(request, board_slug, conversation_id, slug, connection_id):
    user = request.user

    rasa_connection = RasaConversation.objects.get(id=connection_id)
    conversation = Conversation.objects.get(id=conversation_id)

    if (
        user.is_staff
        or user.is_superuser
        or rasa_connection.conversation.author.id == user.id
    ):
        rasa_connection.delete()
    elif rasa_connection.conversation.author.id != user.id:
        raise PermissionError(
            "cannot delete conversation rasa connections from another user"
        )
    else:
        raise PermissionError(
            "user is not allowed to delete conversation rasa connections"
        )

    return redirect(conversation.patch_url("conversation-tools:webchat"))
