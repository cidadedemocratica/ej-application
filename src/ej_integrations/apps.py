from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class EjIntegrationsConfig(AppConfig):
    name = "ej_integrations"
    verbose_name = _("Integrations")
