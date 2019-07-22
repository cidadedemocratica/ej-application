import logging

from allauth.socialaccount import providers
from allauth.socialaccount.models import SocialApp
from allauth.socialaccount.providers.facebook.provider import FacebookProvider
from django.core.exceptions import ImproperlyConfigured

from hyperpython.components import fa_icon

log = logging.getLogger('ej')
SOCIAL_BUTTON_REGISTRY = {}


def register_button(provider_id):
    """
    Register a button tag for the given provider
    """

    def decorator(func):
        SOCIAL_BUTTON_REGISTRY[provider_id] = func
        return func

    return decorator


def active_social_apps(request):
    """
    Return a list of active social apps for the current request.
    """
    # Probably we have to filter the valid providers for the current site.
    return SocialApp.objects.values_list('provider', flat=True)


def social_button(provider_id, request):
    """
    Return a social button for the given provider.
    """
    return SOCIAL_BUTTON_REGISTRY[provider_id](request)


def social_buttons(request):
    """
    Return a list of all active social buttons for the current request.
    """
    return [social_button(id, request) for id in active_social_apps(request)]


@register_button('facebook')
def facebook_button(request):
    provider = providers.registry.by_id('facebook', request)
    query = {
        'next': request.GET.get('next', '/conversations/'),
        'method': 'oauth2',
        'fields': [
            'name',
            'first_name',
            'last_name',
        ]
    }
    url = provider.get_login_url(request, **query)
    return fa_icon('facebook', href=url, id='facebook-button', aria_label="Facebook Icon",
                                            class_='fab fa-facebook icon-facebook rounded-icon')


@register_button('twitter')
def twitter_button(request):
    provider = providers.registry.by_id('twitter', request)
    query = {
        'next': request.GET.get('next', '/conversations/'),
    }
    url = provider.get_login_url(request, **query)
    return fa_icon('twitter', href=url, id='twitter-button', aria_label="Twitter Icon",
                   class_="fab fa-twitter icon-twitter rounded-icon")


@register_button('github')
def github_button(request):
    provider = providers.registry.by_id('github', request)
    query = {
        'next': request.GET.get('next', '/conversations/'),
    }
    url = provider.get_login_url(request, **query)
    return fa_icon('github', href=url, id='github-button')


@register_button('google')
def google_button(request):
    provider = providers.registry.by_id('google', request)
    query = {
        'next': request.GET.get('next', '/conversations/'),
    }
    url = provider.get_login_url(request, **query)
    return fa_icon('google', href=url, id='google-button', aria_label="Google Icon",
                   class_="fab fa-google icon-google rounded-icon")


#
# Monkey patch facebook provider to avoid
#
facebook_media_js = FacebookProvider.media_js


def media_js(self, request):
    try:
        return facebook_media_js(self, request)
    except ImproperlyConfigured as exc:
        log.info(f'ImproperlyConfigured: {exc}')
        return ''


FacebookProvider.media_js = media_js
