import base64
import hashlib
from urllib.parse import parse_qs, urlparse

import pytest
from django.urls import reverse

from ej_govbr.constants import (
    GOVBR_NONCE_SESSION_KEY,
    GOVBR_PROVIDER_ID,
)


@pytest.fixture
def govbr_settings(settings):
    settings.GOVBR_ENABLED = True
    settings.GOVBR_CLIENT_ID = "govbr-client"
    settings.GOVBR_CLIENT_SECRET = "client-secret"
    settings.GOVBR_REDIRECT_URI = (
        "https://ej.example.gov.br/accounts/govbr/login/callback/"
    )
    settings.SOCIALACCOUNT_PROVIDERS = {
        **settings.SOCIALACCOUNT_PROVIDERS,
        GOVBR_PROVIDER_ID: {
            "APP": {
                "name": "GOV.BR",
                "client_id": settings.GOVBR_CLIENT_ID,
                "secret": settings.GOVBR_CLIENT_SECRET,
            }
        },
    }
    return settings


def authorization_parameters(response):
    assert response.status_code == 302
    return parse_qs(urlparse(response.url).query)


def test_govbr_login_is_disabled_by_default(client):
    response = client.get(reverse("govbr_login"))

    assert response.status_code == 404


@pytest.mark.django_db
def test_govbr_login_redirects_with_required_authorization_parameters(
    client, govbr_settings
):
    response = client.get(reverse("govbr_login"), {"next": "/profile/home/"})

    parameters = authorization_parameters(response)
    session = client.session
    states = session["socialaccount_states"]
    state_id, (state, _) = next(iter(states.items()))
    code_verifier = state["pkce_code_verifier"]

    assert response.url.startswith(
        "https://sso.staging.acesso.gov.br/authorize?"
    )
    assert parameters["response_type"] == ["code"]
    assert parameters["client_id"] == ["govbr-client"]
    assert parameters["redirect_uri"] == [govbr_settings.GOVBR_REDIRECT_URI]
    assert set(parameters["scope"][0].split()) == {
        "openid",
        "email",
        "profile",
        "govbr_confiabilidades",
        "govbr_confiabilidades_idtoken",
    }
    assert parameters["state"] == [state_id]
    assert state["next"] == "/profile/home/"
    assert parameters["nonce"] == [session[GOVBR_NONCE_SESSION_KEY]]
    assert parameters["code_challenge_method"] == ["S256"]
    assert 43 <= len(code_verifier) <= 128

    expected_challenge = (
        base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode("ascii")).digest()
        )
        .rstrip(b"=")
        .decode()
    )
    assert parameters["code_challenge"] == [expected_challenge]


@pytest.mark.django_db
def test_govbr_login_ignores_request_scope_and_auth_parameter_overrides(
    client, govbr_settings
):
    response = client.get(
        reverse("govbr_login"),
        {"auth_params": "nonce=attacker", "scope": "phone"},
    )

    parameters = authorization_parameters(response)

    assert parameters["nonce"] == [client.session[GOVBR_NONCE_SESSION_KEY]]
    assert set(parameters["scope"][0].split()) == {
        "openid",
        "email",
        "profile",
        "govbr_confiabilidades",
        "govbr_confiabilidades_idtoken",
    }


@pytest.mark.django_db
def test_govbr_login_discards_unsafe_next_url(client, govbr_settings):
    response = client.get(
        reverse("govbr_login"), {"next": "https://attacker.example/"}
    )

    authorization_parameters(response)
    states = client.session["socialaccount_states"]
    _, (state, _) = next(iter(states.items()))

    assert "next" not in state


@pytest.mark.django_db
def test_govbr_login_generates_a_new_nonce_for_each_request(
    client, govbr_settings
):
    first_response = client.get(reverse("govbr_login"))
    first_nonce = authorization_parameters(first_response)["nonce"][0]

    second_response = client.get(reverse("govbr_login"))
    second_nonce = authorization_parameters(second_response)["nonce"][0]

    assert first_nonce != second_nonce


def test_govbr_callback_route_is_registered(client):
    response = client.get(reverse("govbr_callback"))

    assert response.status_code == 404
