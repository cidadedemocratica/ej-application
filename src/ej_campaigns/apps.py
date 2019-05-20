from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class EjCampaignsConfig(AppConfig):
    name = 'ej_campaigns'
    verbose_name = _('Campaigns')
    rules = None
    api = None

    def ready(self):
        from . import rules, api

        self.rules = rules
        self.api = api
