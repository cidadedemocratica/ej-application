import hashlib
import hmac
from secrets import token_urlsafe
from urllib.parse import urlencode

from allauth.account.models import EmailAddress
from allauth.socialaccount.providers.base import (
    ProviderAccount,
    ProviderException,
)
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider
from django.conf import settings
from django.http import HttpRequest

from .constants import (
    GOVBR_AUTHENTICATED_SESSION_KEY,
    GOVBR_NONCE_SESSION_KEY,
    GOVBR_PROVIDER_ID,
)
from .views import GovBrOAuth2Adapter


def email_is_verified(data):
    value = data.get("email_verified")
    return value is True or value == "true"


def get_logout_redirect_url(request):
    if not request.session.pop(GOVBR_AUTHENTICATED_SESSION_KEY, False):
        return None
    query = urlencode(
        {"post_logout_redirect_uri": settings.GOVBR_POST_LOGOUT_REDIRECT_URI}
    )
    return f"{settings.GOVBR_LOGOUT_URL}?{query}"


class GovBrProvider(OAuth2Provider):
    id = GOVBR_PROVIDER_ID
    name = "GOV.BR"
    account_class = ProviderAccount
    oauth2_adapter_class = GovBrOAuth2Adapter
    pkce_enabled_default = True

    def get_default_scope(self):
        return [
            "openid",
            "email",
            "profile",
            "govbr_confiabilidades",
            "govbr_confiabilidades_idtoken",
        ]

    def get_scope_from_request(self, request: HttpRequest):
        return self.get_scope()

    def get_auth_params_from_request(self, request: HttpRequest, action):
        nonce = token_urlsafe(32)
        request.session[GOVBR_NONCE_SESSION_KEY] = nonce
        params = super().get_auth_params_from_request(request, action)
        params["nonce"] = nonce
        return params

    def extract_uid(self, data):
        subject = data.get("sub")
        if not subject:
            raise ProviderException("Missing GOV.BR subject")
        return hmac.new(
            settings.GOVBR_SUBJECT_HASH_KEY.encode(),
            subject.encode(),
            hashlib.sha256,
        ).hexdigest()

    def extract_extra_data(self, data):
        fields = ("email", "email_verified", "name", "social_name")
        return {field: data[field] for field in fields if field in data}

    def extract_common_fields(self, data):
        email = data.get("email") if email_is_verified(data) else None
        return {
            "email": email,
            "name": data.get("social_name") or data.get("name"),
        }

    def extract_email_addresses(self, data):
        email = data.get("email")
        if email and email_is_verified(data):
            return [EmailAddress(email=email, verified=True, primary=True)]
        return []


provider_classes = [GovBrProvider]
