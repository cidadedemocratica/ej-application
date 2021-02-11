import logging

from boogie.configurations import DjangoConf, env
from .dramatiq import DramatiqConf
from .apps import InstalledAppsConf
from .constance import ConstanceConf
from .email import EmailConf
from .log import LoggingConf
from .middleware import MiddlewareConf
from .notifications import NotificationsConf
from .options import EjOptions
from .paths import PathsConf
from .security import SecurityConf
from .themes import ThemesConf
from .. import fixes

log = logging.getLogger("ej")


class Conf(
    ThemesConf,
    ConstanceConf,
    MiddlewareConf,
    NotificationsConf,
    DramatiqConf,
    SecurityConf,
    LoggingConf,
    PathsConf,
    InstalledAppsConf,
    DjangoConf,
    EjOptions,
    EmailConf,
):
    """
    Configuration class for the EJ platform.

    Settings are created as attributes of a Conf instance and injected in
    the global namespace.
    """

    USING_DOCKER = env(False, name="USING_DOCKER")
    HOSTNAME = env("localhost")

    #
    # Accounts
    #
    AUTH_USER_MODEL = "ej_users.User"
    ACCOUNT_AUTHENTICATION_METHOD = "email"
    ACCOUNT_EMAIL_REQUIRED = True
    ACCOUNT_UNIQUE_EMAIL = True
    ACCOUNT_USERNAME_REQUIRED = False
    ACCOUNT_USER_MODEL_USERNAME_FIELD = None
    LOGIN_REDIRECT_URL = "/"
    ACCOUNT_DEFAULT_HTTP_PROTOCOL = "https"
    ACCOUNT_EMAIL_VERIFICATION = 'none'
    SOCIALACCOUNT_PROVIDERS = {"facebook": {"SCOPE": ["email"], "METHOD": "oauth2"}}

    # MANAGER CONFIGURATION
    # See: https://docs.djangoproject.com/en/dev/ref/settings/#admins
    MANAGERS = ADMINS = [
        ("Bruno Martin, Luan Guimarães, Ricardo Poppi, Henrique Parra", "bruno@hacklab.com.br"),
        ("Laury Bueno", "laury@hacklab.com.br"),
        ("David Carlos", "davidcarlos@pencillabs.com.br"),
    ]

    #
    # Third party modules
    #
    MIGRATION_MODULES = {"sites": "ej.contrib.sites.migrations"}

    EJ_CONVERSATIONS_URLMAP = {
        "conversation-detail": "/conversations/{conversation.slug}/",
        "conversation-list": "conversation:list",
    }

    REST_FRAMEWORK = {
        "DEFAULT_AUTHENTICATION_CLASSES": (
            "rest_framework.authentication.TokenAuthentication",
            # If SessionAuthentication is enabled, a csrf cookie is always set,
            # and token auth does not works.
            # "rest_framework.authentication.SessionAuthentication",
        ),
        "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticatedOrReadOnly",),
        "DEFAULT_RENDERER_CLASSES": (
            "rest_framework.renderers.JSONRenderer",
            "rest_framework.renderers.BrowsableAPIRenderer",
            "ej.settings.custom_api_renders.PlainTextRenderer"),
        "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
        "PAGE_SIZE": 50,
        "DEFAULT_VERSION": "v1",
    }

    # REST_AUTH_REGISTER_SERIALIZERS = {
    #     'REGISTER_SERIALIZER': 'ej_users.serializers.RegistrationSerializer'
    # }

    #
    # Templates
    #
    ACCOUNT_TEMPLATE_EXTENSION = "jinja2"

    import os
    DB_HOST = os.getenv('DB_HOST', 'db')
    if DB_HOST != 'db':
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': 'ej',
                'USER': 'ej',
                'PASSWORD': 'ej',
                'HOST': DB_HOST,
                'PORT': 5432,
            }
        }

    CORS_ORIGIN_ALLOW_ALL = True
    CORS_ORIGIN_WHITELIST = [
        "http://localhost",
        "https://agentesdacidadania.org.br",
        "https://ejplatform.pencillabs.com.br"
    ]

    ALLOWED_HOSTS = ['*']

    REST_AUTH_REGISTER_SERIALIZERS = {
        'REGISTER_SERIALIZER': 'ej_users.rest_auth_serializer.RegistrationSerializer'
    }


Conf.save_settings(globals())

#
# Apply fixes and wait for services to start
#
fixes.apply_all()
