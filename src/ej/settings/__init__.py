import logging
import os

from boogie.configurations import DjangoConf, env
from .apps import InstalledAppsConf
from .constance import ConstanceConf
from .email import EmailConf
from .log import LoggingConf
from .middleware import MiddlewareConf
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
    ACCOUNT_EMAIL_VERIFICATION = "none"
    SOCIALACCOUNT_ADAPTER = "ej_users.adapters.SocialAccountAdapter"
    SOCIALACCOUNT_LOGIN_ON_GET = True
    SOCIALACCOUNT_PROVIDERS = {
        "google": {
            "SCOPE": [
                "profile",
                "email",
            ],
            "AUTH_PARAMS": {
                "access_type": "online",
            },
        }
    }

    # MANAGER CONFIGURATION
    # See: https://docs.djangoproject.com/en/dev/ref/settings/#admins
    MANAGERS = ADMINS = [
        (
            "Bruno Martin, Luan Guimarães, Ricardo Poppi, Henrique Parra",
            "bruno@hacklab.com.br",
        ),
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
            "rest_framework_simplejwt.authentication.JWTAuthentication",
            "rest_framework.authentication.SessionAuthentication",
        ),
        "DEFAULT_PERMISSION_CLASSES": (
            "rest_framework.permissions.IsAuthenticatedOrReadOnly",
        ),
        "DEFAULT_RENDERER_CLASSES": (
            "rest_framework.renderers.JSONRenderer",
            "rest_framework.renderers.BrowsableAPIRenderer",
            "ej.settings.custom_api_renders.PlainTextRenderer",
        ),
        "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
        "PAGE_SIZE": 50,
        "DEFAULT_VERSION": "v1",
        "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    }

    DB_HOST = os.getenv("DB_HOST", "db")
    if DB_HOST != "db":
        DB_NAME = os.getenv("DB_NAME", "ej")
        DB_USER = os.getenv("DB_USER", "ej")
        DB_PASSWORD = os.getenv("DB_PASSWORD", "ej")
        DB_PORT = os.getenv("DB_PORT", 5432)
        DISABLE_SERVER_SIDE_CURSORS = os.getenv("DISABLE_SERVER_SIDE_CURSORS", False)
        CONN_MAX_AGE = os.getenv("CONN_MAX_AGE", 0)
        ATOMIC_REQUESTS = os.getenv("ATOMIC_REQUESTS", False)
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": DB_NAME,
                "USER": DB_USER,
                "PASSWORD": DB_PASSWORD,
                "HOST": DB_HOST,
                "PORT": DB_PORT,
                "DISABLE_SERVER_SIDE_CURSORS": DISABLE_SERVER_SIDE_CURSORS,
                "CONN_MAX_AGE": CONN_MAX_AGE,
                "ATOMIC_REQUESTS": ATOMIC_REQUESTS,
            }
        }

    # django-cors-headers
    CORS_ALLOWED_ORIGINS = (
        []
        if not os.getenv("CORS_ALLOWED_ORIGINS")
        else os.getenv("CORS_ALLOWED_ORIGINS").split(",")
    )

    CSRF_TRUSTED_ORIGINS = (
        []
        if not os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS")
        else os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS").split(",")
    )

    ALLOWED_HOSTS = (
        ["*"]
        if not os.getenv("DJANGO_ALLOWED_HOSTS")
        else os.getenv("DJANGO_ALLOWED_HOSTS").split(",")
    )

    REST_AUTH_REGISTER_SERIALIZERS = {
        "REGISTER_SERIALIZER": "ej_users.rest_auth_serializer.RegistrationSerializer"
    }

    DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }

    # Allow direct TIME_ZONE control, avoiding errors and performance
    # degradation from Django attempting to run SQL SET statements.
    # SQL SET statements are specific to DB poolers session mode, not
    # working with the transaction mode.
    # https://docs.djangoproject.com/en/4.1/topics/i18n/timezones/#postgresql
    if os.getenv("TIME_ZONE"):
        USE_TZ = os.getenv("USE_TZ", False)
        TIME_ZONE = os.getenv("TIME_ZONE", "America/Sao_Paulo")

    # The persona's managing form uses a Formset to send the comments and their votes
    # to the backend using a POST request. In a conversation with several comments, Django
    # will complain about the number of uploaded fields during the request.
    # This variable increases this limit.
    DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000


Conf.save_settings(globals())

#
# Apply fixes and wait for services to start
#
fixes.apply_all()
