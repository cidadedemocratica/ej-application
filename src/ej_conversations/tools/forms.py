from django import forms
from django.template.loader import get_template
from django.utils.translation import ugettext_lazy as _

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

class AuthWidget(forms.RadioSelect):
    template_name = "ej_conversations_tools/includes/auth-select.jinja2"
    renderer = get_template(template_name)

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return self.renderer.render(context)


class ConversationComponentForm(forms.Form):
    authentication_type = forms.ChoiceField(
        label=_("Authentication Type"), choices=AUTH_TYPE_CHOICES,
        required=False, widget=AuthWidget(attrs=AUTH_TOOLTIP_TEXTS)
    )
    theme = forms.ChoiceField(
        label=_("Theme"), choices=THEME_CHOICES,
        required=False, widget=forms.RadioSelect
    )
