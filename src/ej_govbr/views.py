from allauth.socialaccount.adapter import get_adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Error
from allauth.socialaccount.providers.oauth2.views import (
    OAuth2Adapter,
    OAuth2CallbackView,
    OAuth2LoginView,
)
from django.conf import settings
from django.http import Http404

from .constants import GOVBR_NONCE_SESSION_KEY, GOVBR_PROVIDER_ID
from .tokens import validate_id_token


class GovBrOAuth2Adapter(OAuth2Adapter):
    provider_id = GOVBR_PROVIDER_ID
    basic_auth = True

    @property
    def access_token_url(self):
        return settings.GOVBR_TOKEN_URL

    @property
    def authorize_url(self):
        return settings.GOVBR_AUTHORIZE_URL

    def get_callback_url(self, request, app):
        return settings.GOVBR_REDIRECT_URI

    def complete_login(self, request, app, token, response, **kwargs):
        nonce = request.session.pop(GOVBR_NONCE_SESSION_KEY, None)
        if not nonce:
            raise OAuth2Error("Missing GOV.BR login nonce")
        try:
            id_token = response["id_token"]
            jwks_response = (
                get_adapter()
                .get_requests_session()
                .get(settings.GOVBR_JWKS_URL)
            )
            jwks_response.raise_for_status()
            claims = validate_id_token(
                id_token,
                jwks_response.json(),
                audience=settings.GOVBR_CLIENT_ID,
                issuer=settings.GOVBR_ISSUER,
                nonce=nonce,
            )
        except (KeyError, ValueError):
            raise OAuth2Error("Invalid GOV.BR ID token") from None
        return self.get_provider().sociallogin_from_response(request, claims)


class GovBrOAuth2LoginView(OAuth2LoginView):
    def dispatch(self, request, *args, **kwargs):
        if not settings.GOVBR_ENABLED:
            raise Http404
        return super().dispatch(request, *args, **kwargs)


oauth2_login = GovBrOAuth2LoginView.adapter_view(GovBrOAuth2Adapter)


class GovBrOAuth2CallbackView(OAuth2CallbackView):
    def dispatch(self, request, *args, **kwargs):
        if not settings.GOVBR_ENABLED:
            raise Http404
        return super().dispatch(request, *args, **kwargs)


oauth2_callback = GovBrOAuth2CallbackView.adapter_view(GovBrOAuth2Adapter)
