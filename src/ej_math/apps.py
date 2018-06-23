from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class EjMathConfig(AppConfig):
    name = 'ej_math'
    verbose_name = _('Math')

    def ready(self):
        from .clusters_patch import patch
        patch()
