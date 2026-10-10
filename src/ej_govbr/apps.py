from django.apps import AppConfig


class EjGovBrConfig(AppConfig):
    name = "ej_govbr"
    verbose_name = "GOV.BR login"

    def ready(self):
        from . import signals  # noqa: F401
