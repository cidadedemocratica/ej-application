import logging

from allauth.socialaccount import providers
from allauth.socialaccount.models import SocialApp
from allauth.socialaccount.providers.facebook.provider import FacebookProvider
from django.apps import apps
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse
from hyperpython.components import fa_icon

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
        active_apps = SocialApp.objects.values_list("provider", flat=True)
        return [social_button(id_, request) for id_ in active_apps]
    else:
        return ()


def register_button(provider_id, fa_class=None, query=None):
    """
    Register a button tag for the given provider
    """
    fa_class = fa_class or "fa-" + provider_id

    def social_button(request):
        redirect_url = reverse("conversation:list")
        provider = providers.registry.by_id(provider_id, request)
        url = provider.get_login_url(
            request, next=request.GET.get("next", redirect_url), **(query or {})
        )

        return fa_icon(
            provider_id,
            href=url,
            id=f"{provider_id}-button",
            aria_label=f"{provider_id.title()} Icon",
            class_=f"fab {fa_class} icon-{provider_id} rounded-icon",
        )

    SOCIAL_BUTTON_REGISTRY[provider_id] = social_button
    return social_button


register_button("facebook", query={"method", "oauth2"})
register_button("twitter")
register_button("github")
register_button("google", fa_class="fa-google-plus-g")


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
