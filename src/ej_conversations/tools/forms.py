from django import forms
from django.utils.translation import ugettext_lazy as _

AUTH_TYPE_CHOICES =( 
    ("register", _("Register using email")), 
    ("mautic", _("Mautic")), 
    ("analytics", _("Analytics")),
)

THEME_CHOICES =( 
    ("", _("Default")), 
    ("votorantim", _("Votorantim")), 
    ("icd", _("ICD")),
)

class ConversationComponentForm(forms.Form): 
    authentication_type = forms.ChoiceField(label=_("Authentication Type"), choices=AUTH_TYPE_CHOICES, required=False)
    theme = forms.ChoiceField(label=_("Theme"), choices=THEME_CHOICES, required=False) 