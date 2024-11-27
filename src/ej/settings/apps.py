from boogie.configurations import InstalledAppsConf as Base
from boogie.configurations import env
from importlib import import_module
from logging import getLogger
import os

from .options import EjOptions

log = getLogger("ej")


class InstalledAppsConf(Base, EjOptions):
    USE_DJANGO_ADMIN = env(True, name="{attr}")
    DISABLE_DJANGO_DEBUG_TOOLBAR = env(True, name="{attr}")

    project_apps = [
        "ej_boards",
        "ej_clusters",
        "ej_dataviz",
        "ej_profiles",
        "ej_conversations",
        "ej_integrations",
        "ej_admin",
    ]

    third_party_apps = [
        "taggit",
        "rules",
        "allauth",
        "allauth.account",
        "allauth.socialaccount",
        "allauth.socialaccount.providers.google",
        "ej_users",
        "rest_framework",
        "rest_framework.authtoken",
        "corsheaders",
        "django.contrib.auth",
        "django.contrib.messages",
        "django.contrib.sites",
        "django.contrib.postgres",
        "constance",
        "constance.backends.database",
        "anymail",
        "ckeditor",
        "drf_spectacular",
        "django.contrib.admin",
    ]

    def get_django_contrib_apps(self):
        return [*super().get_django_contrib_apps(), "django.contrib.flatpages"]

    def get_project_apps(self):
        project_apps = [*super().get_project_apps(), *self.project_apps]
        return [*project_apps, *self.get_submodule_apps()]

    def get_submodule_apps(self):
        """
        Dynamically includes Django apps in the project_apps attribute.
        It searches src subdirectories looking for apps with
        IS_SUBMODULE global variable and adds them to self.project_apps.
        """
        apps = os.listdir(f"{os.getcwd()}/src")
        additional_apps = [app for app in apps if app not in self.project_apps]
        submodule_apps = []
        for app in additional_apps:
            try:
                # app_module is the apps.py file inside each Django app.
                app_module = import_module(f"{app}.apps")
                if getattr(app_module, "IS_SUBMODULE"):
                    submodule_apps.append(app)
                    log.info(f"Adding {app} app to project apps list")
            except Exception:
                pass
        return submodule_apps

    def get_third_party_apps(self):
        apps = [*super().get_third_party_apps(), *self.third_party_apps]
        if self.ENVIRONMENT == "local":
            if not self.DISABLE_DJANGO_DEBUG_TOOLBAR:
                apps = ["debug_toolbar", *apps]

        elif self.DEBUG and not self.DISABLE_DJANGO_DEBUG_TOOLBAR:
            apps = ["debug_toolbar", *apps]
        if self.ENVIRONMENT == "production":
            apps = ["gunicorn", *apps]
        return apps
