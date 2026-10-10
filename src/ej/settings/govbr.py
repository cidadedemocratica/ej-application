from urllib.parse import urlparse

from django.core.exceptions import ImproperlyConfigured


REQUIRED_GOVBR_SETTINGS = (
    "GOVBR_CLIENT_ID",
    "GOVBR_CLIENT_SECRET",
    "GOVBR_SUBJECT_HASH_KEY",
    "GOVBR_REDIRECT_URI",
    "GOVBR_POST_LOGOUT_REDIRECT_URI",
    "GOVBR_AUTHORIZE_URL",
    "GOVBR_TOKEN_URL",
    "GOVBR_JWKS_URL",
    "GOVBR_LOGOUT_URL",
    "GOVBR_ISSUER",
)

GOVBR_URL_SETTINGS = (
    "GOVBR_REDIRECT_URI",
    "GOVBR_POST_LOGOUT_REDIRECT_URI",
    "GOVBR_AUTHORIZE_URL",
    "GOVBR_TOKEN_URL",
    "GOVBR_JWKS_URL",
    "GOVBR_LOGOUT_URL",
    "GOVBR_ISSUER",
)


def validate_govbr_settings(settings):
    if not settings.get("GOVBR_ENABLED", False):
        return

    missing = [
        setting
        for setting in REQUIRED_GOVBR_SETTINGS
        if not settings.get(setting)
    ]
    if missing:
        names = ", ".join(missing)
        raise ImproperlyConfigured(
            f"GOV.BR login requires these settings: {names}"
        )

    invalid_urls = [
        setting
        for setting in GOVBR_URL_SETTINGS
        if (
            (url := urlparse(settings[setting])).scheme != "https"
            or not url.netloc
        )
    ]
    if invalid_urls:
        names = ", ".join(invalid_urls)
        raise ImproperlyConfigured(f"GOV.BR login requires HTTPS URLs: {names}")
