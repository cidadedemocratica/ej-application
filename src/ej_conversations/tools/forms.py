from django import forms
from django.template.loader import get_template
from django.utils.translation import ugettext_lazy as _

from ej_boards.forms import PaletteWidget
from ej.forms import EjModelForm
from .models import RasaConversation


class ConversationComponent:
    AUTH_TYPE_CHOICES = (
        ("register", _("Register using name/email")),
        ("mautic", _("Mautic")),
        ("analytics", _("Analytics")),
    )

    AUTH_TOOLTIP_TEXTS = {
        "register": _("User will use EJ platform interface, creating an account using personal data"),
        "mautic": _("Uses a mautic campaign "),
        "analytics": _("Uses analytics cookies allowing you to cross vote data with user browser data.")
    }

    THEME_CHOICES = (
        ("default", _("Default")),
        ("votorantim", _("Votorantim")),
        ("icd", _("ICD")),
    )

    THEME_PALETTES = {
        "default": ["#1D1088", "#F8127E"],
        "votorantim": ["#04082D", "#F14236"],
        "icd": ["#005BAA", "#F5821F"]
    }

    def __init__(self, form):
        self.form = form

    def get_props(self):
        if self.form.is_valid():
            result = ""

            if not self.form.cleaned_data["theme"] == "default":
                result = result + f"theme={self.form.cleaned_data['theme']} "
            if self.form.cleaned_data["authentication_type"]:
                result = result + f" authenticate-with={self.form.cleaned_data['authentication_type']}"
            return result
        return "authenticate-with=register"

class AuthWidget(forms.RadioSelect):
    template_name = "ej_conversations_tools/includes/auth-select.jinja2"
    renderer = get_template(template_name)

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return self.renderer.render(context)

class ConversationComponentForm(forms.Form):
    authentication_type = forms.ChoiceField(
        label=_("Authentication Type"), choices=ConversationComponent.AUTH_TYPE_CHOICES,
        required=False, widget=AuthWidget(attrs=ConversationComponent.AUTH_TOOLTIP_TEXTS)
    )
    theme = forms.ChoiceField(
        label=_("Theme"), choices=ConversationComponent.THEME_CHOICES,
        required=False, widget=PaletteWidget
    )

class RasaConversationForm(EjModelForm):
    class Meta:
        model = RasaConversation
        fields = ["conversation", "domain"]
        help_texts = {"conversation": None, "domain": None}

    def __init__(self, *args, conversation, **kwargs):
        kwargs.update(initial={
        'conversation': conversation
        })
        super(RasaConversationForm, self).__init__(*args, **kwargs)
