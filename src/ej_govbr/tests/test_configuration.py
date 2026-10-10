import pytest
from django.apps import apps
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from ej.settings.govbr import (
    GOVBR_URL_SETTINGS,
    REQUIRED_GOVBR_SETTINGS,
    validate_govbr_settings,
)


def govbr_settings():
    return {
        "GOVBR_ENABLED": True,
        "GOVBR_CLIENT_ID": "govbr-client",
        "GOVBR_CLIENT_SECRET": "client-secret",
        "GOVBR_SUBJECT_HASH_KEY": "subject-hash-key",
        "GOVBR_REDIRECT_URI": "https://ej.example.gov.br/accounts/govbr/login/callback/",
        "GOVBR_POST_LOGOUT_REDIRECT_URI": "https://ej.example.gov.br/login/",
        "GOVBR_AUTHORIZE_URL": "https://sso.staging.acesso.gov.br/authorize",
        "GOVBR_TOKEN_URL": "https://sso.staging.acesso.gov.br/token",
        "GOVBR_JWKS_URL": "https://sso.staging.acesso.gov.br/jwk",
        "GOVBR_LOGOUT_URL": "https://sso.staging.acesso.gov.br/logout",
        "GOVBR_ISSUER": "https://sso.staging.acesso.gov.br/",
    }


def test_govbr_is_disabled_by_default():
    assert settings.GOVBR_ENABLED is False


def test_govbr_provider_app_is_installed():
    assert apps.is_installed("ej_govbr")


def test_disabled_govbr_does_not_require_configuration():
    validate_govbr_settings({"GOVBR_ENABLED": False})


def test_enabled_govbr_accepts_complete_configuration():
    validate_govbr_settings(govbr_settings())


@pytest.mark.parametrize("setting", REQUIRED_GOVBR_SETTINGS)
def test_enabled_govbr_rejects_missing_required_setting(setting):
    configured = govbr_settings()
    configured[setting] = ""

    with pytest.raises(ImproperlyConfigured, match=setting):
        validate_govbr_settings(configured)


@pytest.mark.parametrize("setting", GOVBR_URL_SETTINGS)
@pytest.mark.parametrize("value", ["http://example.gov.br/", "not-a-url"])
def test_enabled_govbr_rejects_invalid_url_setting(setting, value):
    configured = govbr_settings()
    configured[setting] = value

    with pytest.raises(ImproperlyConfigured, match=setting):
        validate_govbr_settings(configured)
