from django import forms
from django.template.loader import get_template
from django.utils.translation import gettext_lazy as _

from django.core.exceptions import ValidationError
from django.db.models import Q

from ej_boards.forms import PaletteWidget
from ej_conversations.models import Comment, Conversation
from ej.forms import EjModelForm
from ej_integrations.models import (
    RasaConversation,
    OpinionComponent,
)
from ej_integrations.tools import MailingTool


class CustomChoiceWidget(forms.RadioSelect):
    template_name = "ej_integrations/includes/custom-select.jinja2"
    renderer = get_template(template_name)

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return self.renderer.render(context)


class CustomTemplateChoiceWidget(forms.RadioSelect):
    template_name = "ej_integrations/includes/template-type.jinja2"
    renderer = get_template(template_name)

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return self.renderer.render(context)


class OpinionComponentForm(forms.ModelForm):
    conversation = forms.ModelChoiceField(
        widget=forms.HiddenInput(), queryset=Conversation.objects.all()
    )

    class Meta:
        model = OpinionComponent
        fields = "__all__"


class MailingToolForm(forms.Form):
    template_type = forms.ChoiceField(
        label=_("Template type"),
        choices=MailingTool.MAILING_TOOL_CHOICES,
        required=False,
        widget=CustomTemplateChoiceWidget(attrs=MailingTool.MAILING_TOOLTIP_TEXTS),
    )
    theme = forms.ChoiceField(
        label=_("Theme"),
        choices=MailingTool.THEME_CHOICES,
        required=False,
        widget=PaletteWidget,
    )
    is_custom_domain = forms.BooleanField(
        required=False, label=_("Redirect user to a custom domain (optional)")
    )
    custom_title = forms.CharField(
        required=False, label=_("Adds a custom title to the template (optional).")
    )
    custom_comment = forms.ModelChoiceField(
        queryset=None,
        required=False,
        label=_("selects a specific comment for user to vote (optional)."),
    )

    def __init__(self, *args, **kwargs):
        conversation_id = kwargs.pop("conversation_id")
        super(MailingToolForm, self).__init__(*args, **kwargs)
        self.fields["custom_comment"].queryset = Comment.objects.filter(
            conversation=conversation_id
        )


class RasaConversationForm(EjModelForm):
    def clean_domain(self):
        incoming_domain = str(self.cleaned_data["domain"])
        if incoming_domain[-1] == "/":
            incoming_domain = str(self.cleaned_data["domain"])[:-1]
        domain = RasaConversation.objects.filter(
            Q(domain=incoming_domain) | Q(domain=incoming_domain + "/")
        ).first()
        if domain is None:
            return self.cleaned_data["domain"]
        if domain.conversation == self.cleaned_data["conversation"]:
            raise ValidationError(
                _("Rasa conversation with this Conversation and Domain already exists.")
            )
        raise ValidationError(
            _(
                "Site already integrated with conversation %(conversation)s, try another url."
            ),
            params={"conversation": domain.conversation},
        )

    class Meta:
        model = RasaConversation
        fields = ["conversation", "domain"]
        help_texts = {"conversation": None, "domain": None}
