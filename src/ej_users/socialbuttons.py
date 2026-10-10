import logging
from urllib.parse import urlencode

from allauth.socialaccount import providers
from allauth.socialaccount.models import SocialApp
from allauth.socialaccount.providers.facebook.provider import FacebookProvider
from django.apps import apps
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from ej_govbr.constants import GOVBR_PROVIDER_ID

log = logging.getLogger("ej")
SOCIAL_BUTTON_REGISTRY = {}


def social_button(provider_id, request):
    """
    Return a social button for the given provider.
    """
    return SOCIAL_BUTTON_REGISTRY[provider_id](request)


def social_buttons(request):
    """
    Return a list of all active social buttons for the current request.
    """
    if apps.is_installed("allauth.socialaccount"):
        provider_ids = ["google"]
        if settings.GOVBR_ENABLED:
            provider_ids.append(GOVBR_PROVIDER_ID)
        return [
            button
            for provider_id in provider_ids
            if (button := social_button(provider_id, request))["href"]
        ]
    else:
        return ()


def register_button(
    provider_id, fa_class=None, query=None, login_url_name=None, label=None
):
    """
    Register a button tag for the given provider
    """
    fa_class = fa_class or "fa-" + provider_id

    def social_button(request):
        redirect_url = reverse("profile:home")
        next_url = request.GET.get("next", redirect_url)
        if login_url_name:
            url = reverse(login_url_name)
            return {
                "provider": provider_id,
                "href": f"{url}?{urlencode({'next': next_url})}",
                "id": f"{provider_id}-button",
                "class_": fa_class,
                "label": label,
            }
        providers_classes = providers.registry.get_class_list()

        try:
            Provider = list(
                filter(
                    lambda provider: provider.id == provider_id,
                    providers_classes,
                )
            )[0]
            app = SocialApp.objects.get(provider=provider_id)
            provider = Provider(request, app)
            url = provider.get_login_url(
                request,
                next=next_url,
                **(query or {}),
            )
            return {
                "provider": provider_id,
                "href": url,
                "id": f"{provider_id}-button",
                "class_": f"{fa_class} icon-{provider_id} rounded-icon",
                "label": label or provider_id.title(),
            }
        except Exception as e:
            log.error(f"{e}")

        return {
            "provider": "",
            "href": "",
            "id": "",
            "class_": "",
            "label": "",
        }

    SOCIAL_BUTTON_REGISTRY[provider_id] = social_button
    return social_button


register_button(
    "google", fa_class="fab fa-google", label=_("Sign in with Google")
)
register_button(
    GOVBR_PROVIDER_ID,
    login_url_name="govbr_login",
    label=_("Sign in with GOV.BR"),
)


#
# Monkey patch facebook provider to avoid login problem when no Facebook app
# is configured.
#
def fix_facebook_provider():
    facebook_media_js = FacebookProvider.media_js

    def media_js(self, request):
        try:
            return facebook_media_js(self, request)
        except ImproperlyConfigured as exc:
            log.info(f"ImproperlyConfigured: {exc}")
            return ""

    FacebookProvider.media_js = media_js


fix_facebook_provider()
