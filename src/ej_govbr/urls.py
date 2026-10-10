from allauth.socialaccount.providers.oauth2.urls import default_urlpatterns

from .provider import GovBrProvider


urlpatterns = default_urlpatterns(GovBrProvider)
