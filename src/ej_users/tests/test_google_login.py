from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import pytest
from allauth.socialaccount.forms import SignupForm
from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site
from django.urls import reverse

from ej_govbr.forms import SignupFormRouter


@pytest.fixture
def google_app(db):
    app = SocialApp.objects.create(
        provider="google",
        name="Google",
        client_id="google-client",
        secret="google-secret",
    )
    app.sites.add(Site.objects.get_current())
    return app


@pytest.mark.django_db
def test_google_button_is_rendered_on_login(client, google_app):
    response = client.get(reverse("auth:login"))

    assert response.status_code == 200
    assert b'id="google-button"' in response.content
    assert b"/accounts/google/login/?next=" in response.content


def test_google_signup_uses_the_default_allauth_form():
    sociallogin = SimpleNamespace(account=SimpleNamespace(provider="google"))

    assert SignupFormRouter.get_form_class(sociallogin) is SignupForm


@pytest.mark.django_db
def test_google_login_redirects_to_google_authorization(client, google_app):
    response = client.get(reverse("google_login"), {"next": "/profile/home/"})

    assert response.status_code == 302
    parsed = urlparse(response.url)
    parameters = parse_qs(parsed.query)

    assert parsed.netloc == "accounts.google.com"
    assert parameters["client_id"] == ["google-client"]
    assert parameters["response_type"] == ["code"]
    assert "state" in parameters
