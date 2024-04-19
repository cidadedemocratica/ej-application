from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class EjDatavizConfig(AppConfig):
    name = "ej_dataviz"
    verbose_name = _("Visualization")
    rules = None
    roles = None

    def ready(self):
        from . import rules

        self.rules = rules
