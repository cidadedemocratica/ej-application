import json
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from django.http import HttpResponse
from django.urls import reverse
from jwt.algorithms import RSAAlgorithm
from allauth.account.models import EmailAddress, EmailConfirmationHMAC
from allauth.socialaccount.models import SocialAccount, SocialToken

from ej_users.models import User
from ej_govbr.constants import (
    GOVBR_AUTHENTICATED_SESSION_KEY,
    GOVBR_PROVIDER_ID,
)


class FakeResponse:
    def __init__(self, data):
        self.data = data
        self.status_code = 200
        self.headers = {"content-type": "application/json"}
        self.text = json.dumps(data)
        self.content = self.text.encode()

    def json(self):
        return self.data

    def raise_for_status(self):
        return None


class FakeRequestsSession:
    def __init__(self, id_token, jwks):
        self.id_token = id_token
        self.jwks = jwks
        self.requests = []
        self.jwks_urls = []

    def request(self, *args, **kwargs):
        self.requests.append((args, kwargs))
        return FakeResponse(
            {"access_token": "access-token", "id_token": self.id_token}
        )

    def get(self, url):
        self.jwks_urls.append(url)
        return FakeResponse(self.jwks)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


@pytest.fixture
def govbr_settings(settings):
    settings.GOVBR_ENABLED = True
    settings.GOVBR_CLIENT_ID = "govbr-client"
    settings.GOVBR_CLIENT_SECRET = "client-secret"
    settings.GOVBR_SUBJECT_HASH_KEY = "subject-hash-key"
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


@pytest.fixture
def signing_key():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(RSAAlgorithm.to_jwk(private_key.public_key()))
    jwk.update({"alg": "RS256", "kid": "govbr-signing-key", "use": "sig"})
    return private_key, jwk


def start_login(client, next_url=None):
    response = client.get(
        reverse("govbr_login"), {"next": next_url} if next_url else {}
    )
    parameters = parse_qs(urlparse(response.url).query)
    return parameters["state"][0], parameters["nonce"][0]


def id_token(settings, private_key, jwk, default_nonce, **overrides):
    claims = {
        "aud": settings.GOVBR_CLIENT_ID,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        "iss": settings.GOVBR_ISSUER,
        "nonce": default_nonce,
        "sub": "12345678900",
    }
    claims.update(overrides)
    return jwt.encode(
        claims,
        private_key,
        algorithm="RS256",
        headers={"kid": jwk["kid"]},
    )


def callback(client, state, requests_session):
    with patch(
        "ej_users.adapters.SocialAccountAdapter.get_requests_session",
        return_value=requests_session,
    ), patch(
        "allauth.socialaccount.providers.oauth2.views.complete_social_login",
        return_value=HttpResponse(status=204),
    ) as complete_login:
        response = client.get(
            reverse("govbr_callback"),
            {"code": "authorization-code", "state": state},
        )
    return response, complete_login


def complete_callback(client, state, requests_session):
    with patch(
        "ej_users.adapters.SocialAccountAdapter.get_requests_session",
        return_value=requests_session,
    ):
        return client.get(
            reverse("govbr_callback"),
            {"code": "authorization-code", "state": state},
        )


@pytest.mark.django_db
def test_callback_exchanges_pkce_code_and_validates_id_token(
    client, govbr_settings, signing_key
):
    private_key, jwk = signing_key
    state, nonce = start_login(client)
    requests_session = FakeRequestsSession(
        id_token(govbr_settings, private_key, jwk, nonce), {"keys": [jwk]}
    )

    response, complete_login = callback(client, state, requests_session)

    assert response.status_code == 204
    assert len(requests_session.requests) == 1
    request_args, request_kwargs = requests_session.requests[0]
    assert request_args == ("POST", govbr_settings.GOVBR_TOKEN_URL)
    assert request_kwargs["auth"].username == govbr_settings.GOVBR_CLIENT_ID
    assert request_kwargs["auth"].password == govbr_settings.GOVBR_CLIENT_SECRET
    assert request_kwargs["data"]["code"] == "authorization-code"
    assert request_kwargs["data"]["code_verifier"]
    assert (
        request_kwargs["data"]["redirect_uri"]
        == govbr_settings.GOVBR_REDIRECT_URI
    )
    assert requests_session.jwks_urls == [govbr_settings.GOVBR_JWKS_URL]

    social_login = complete_login.call_args.args[1]
    assert SocialToken.objects.count() == 0
    assert "id_token" not in social_login.account.extra_data
    assert social_login.account.uid != "12345678900"
    assert "sub" not in social_login.account.extra_data
    assert "govbr_nonce" not in client.session
    assert not client.session.get("socialaccount_states")


@pytest.mark.django_db
def test_callback_rejects_invalid_state_before_token_exchange(
    client, govbr_settings, signing_key
):
    private_key, jwk = signing_key
    _, nonce = start_login(client)
    requests_session = FakeRequestsSession(
        id_token(govbr_settings, private_key, jwk, nonce), {"keys": [jwk]}
    )

    response, complete_login = callback(client, "wrong-state", requests_session)

    assert response.url == reverse("auth:login")
    assert not requests_session.requests
    assert not requests_session.jwks_urls
    complete_login.assert_not_called()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "overrides",
    [
        {"aud": "other-client"},
        {"exp": datetime.now(timezone.utc) - timedelta(minutes=5)},
        {"iss": "https://other.example/"},
        {"nonce": "wrong-nonce"},
        {"sub": ""},
        {"aud": ["govbr-client", "other-client"]},
        {
            "aud": ["govbr-client", "other-client"],
            "azp": "other-client",
        },
    ],
)
def test_callback_rejects_invalid_id_token_claims(
    client, govbr_settings, signing_key, overrides
):
    private_key, jwk = signing_key
    state, nonce = start_login(client)
    overrides.setdefault("nonce", nonce)
    requests_session = FakeRequestsSession(
        id_token(govbr_settings, private_key, jwk, nonce, **overrides),
        {"keys": [jwk]},
    )

    response, complete_login = callback(client, state, requests_session)

    assert response.url == reverse("auth:login")
    complete_login.assert_not_called()


@pytest.mark.django_db
def test_callback_rejects_invalid_signature(
    client, govbr_settings, signing_key
):
    _, jwk = signing_key
    different_key = rsa.generate_private_key(
        public_exponent=65537, key_size=2048
    )
    state, nonce = start_login(client)
    requests_session = FakeRequestsSession(
        id_token(govbr_settings, different_key, jwk, nonce), {"keys": [jwk]}
    )

    response, complete_login = callback(client, state, requests_session)

    assert response.url == reverse("auth:login")
    complete_login.assert_not_called()


@pytest.mark.django_db
def test_callback_rejects_unsupported_signing_algorithm(
    client, govbr_settings, signing_key
):
    private_key, jwk = signing_key
    state, nonce = start_login(client)
    unsupported_token = jwt.encode(
        {
            "aud": govbr_settings.GOVBR_CLIENT_ID,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
            "iss": govbr_settings.GOVBR_ISSUER,
            "nonce": nonce,
            "sub": "12345678900",
        },
        "not-an-rsa-key-that-is-long-enough",
        algorithm="HS256",
        headers={"kid": jwk["kid"]},
    )
    requests_session = FakeRequestsSession(unsupported_token, {"keys": [jwk]})

    response, complete_login = callback(client, state, requests_session)

    assert response.url == reverse("auth:login")
    complete_login.assert_not_called()


@pytest.mark.django_db
@pytest.mark.parametrize("email_verified", [True, "true"])
def test_callback_creates_a_user_with_a_hashed_govbr_identity(
    client, govbr_settings, signing_key, email_verified
):
    private_key, jwk = signing_key
    state, nonce = start_login(client)
    requests_session = FakeRequestsSession(
        id_token(
            govbr_settings,
            private_key,
            jwk,
            nonce,
            email="citizen@example.gov.br",
            email_verified=email_verified,
            name="Legal name",
            social_name="Social name",
        ),
        {"keys": [jwk]},
    )

    response = complete_callback(client, state, requests_session)

    user = User.objects.get(email="citizen@example.gov.br")
    account = SocialAccount.objects.get(user=user, provider=GOVBR_PROVIDER_ID)
    expected_uid = hmac.new(
        govbr_settings.GOVBR_SUBJECT_HASH_KEY.encode(),
        b"12345678900",
        hashlib.sha256,
    ).hexdigest()

    assert response.status_code == 302
    assert not user.has_usable_password()
    assert user.name == "Social name"
    assert account.uid == expected_uid
    assert "sub" not in account.extra_data
    assert client.session["_auth_user_id"] == str(user.id)
    assert client.session[GOVBR_AUTHENTICATED_SESSION_KEY]


@pytest.mark.django_db
@pytest.mark.parametrize("email_verified", [True, "true"])
def test_callback_links_a_verified_govbr_email_to_an_existing_user(
    client, govbr_settings, signing_key, email_verified
):
    existing_user = User.objects.create_user(
        "existing@example.gov.br", "password", name="Existing user"
    )
    private_key, jwk = signing_key
    state, nonce = start_login(client)
    requests_session = FakeRequestsSession(
        id_token(
            govbr_settings,
            private_key,
            jwk,
            nonce,
            email=existing_user.email,
            email_verified=email_verified,
        ),
        {"keys": [jwk]},
    )

    response = complete_callback(client, state, requests_session)

    account = SocialAccount.objects.get(provider=GOVBR_PROVIDER_ID)

    assert response.status_code == 302
    assert account.user == existing_user
    assert User.objects.count() == 1


@pytest.mark.django_db
@pytest.mark.parametrize("email_verified", [False, "false"])
def test_callback_does_not_link_an_unverified_govbr_email(
    client, govbr_settings, signing_key, email_verified
):
    existing_user = User.objects.create_user(
        "existing@example.gov.br", "password", name="Existing user"
    )
    private_key, jwk = signing_key
    state, nonce = start_login(client)
    requests_session = FakeRequestsSession(
        id_token(
            govbr_settings,
            private_key,
            jwk,
            nonce,
            email=existing_user.email,
            email_verified=email_verified,
        ),
        {"keys": [jwk]},
    )

    response = complete_callback(client, state, requests_session)

    assert response.url == reverse("socialaccount_signup")
    assert not SocialAccount.objects.filter(provider=GOVBR_PROVIDER_ID).exists()
    assert User.objects.count() == 1


@pytest.mark.django_db
def test_callback_reuses_govbr_identity_when_the_email_changes(
    client, govbr_settings, signing_key
):
    private_key, jwk = signing_key
    first_state, first_nonce = start_login(client)
    first_response = complete_callback(
        client,
        first_state,
        FakeRequestsSession(
            id_token(
                govbr_settings,
                private_key,
                jwk,
                first_nonce,
                email="first@example.gov.br",
                email_verified=True,
            ),
            {"keys": [jwk]},
        ),
    )
    first_user = User.objects.get(email="first@example.gov.br")
    client.logout()

    second_state, second_nonce = start_login(client)
    second_response = complete_callback(
        client,
        second_state,
        FakeRequestsSession(
            id_token(
                govbr_settings,
                private_key,
                jwk,
                second_nonce,
                email="changed@example.gov.br",
                email_verified=True,
            ),
            {"keys": [jwk]},
        ),
    )

    account = SocialAccount.objects.get(provider=GOVBR_PROVIDER_ID)

    assert first_response.status_code == 302
    assert second_response.status_code == 302
    assert account.user_id == first_user.id
    assert User.objects.count() == 1
    assert User.objects.get(id=first_user.id).email == "first@example.gov.br"


@pytest.mark.django_db
def test_unverified_govbr_email_requires_registration_completion(
    client, govbr_settings, signing_key
):
    private_key, jwk = signing_key
    state, nonce = start_login(client)
    signup_response = complete_callback(
        client,
        state,
        FakeRequestsSession(
            id_token(
                govbr_settings,
                private_key,
                jwk,
                nonce,
                email="unverified@example.gov.br",
                email_verified=False,
            ),
            {"keys": [jwk]},
        ),
    )

    response = client.get(signup_response.url)
    incomplete_response = client.post(
        signup_response.url, {"email": "citizen@example.gov.br"}
    )

    assert response.status_code == 200
    assert response.context["form"].__class__.__name__ == "GovBrSignupForm"
    assert incomplete_response.status_code == 200
    assert User.objects.count() == 0
    assert not SocialAccount.objects.filter(provider=GOVBR_PROVIDER_ID).exists()
    assert GOVBR_AUTHENTICATED_SESSION_KEY not in client.session


@pytest.mark.django_db
def test_govbr_registration_confirms_email_before_logging_in(
    client, govbr_settings, signing_key
):
    private_key, jwk = signing_key
    state, nonce = start_login(client, "/profile/home/")
    signup_response = complete_callback(
        client,
        state,
        FakeRequestsSession(
            id_token(
                govbr_settings,
                private_key,
                jwk,
                nonce,
                email_verified=False,
            ),
            {"keys": [jwk]},
        ),
    )

    completion_response = client.post(
        signup_response.url,
        {
            "email": "citizen@example.gov.br",
            "agree_with_terms": True,
            "agree_with_privacy_policy": True,
        },
    )
    user = User.objects.get(email="citizen@example.gov.br")
    email_address = EmailAddress.objects.get(user=user)
    confirmation_url = reverse(
        "account_confirm_email", args=[EmailConfirmationHMAC(email_address).key]
    )

    assert completion_response.url == reverse("account_email_verification_sent")
    assert "_auth_user_id" not in client.session
    assert not email_address.verified
    assert user.agree_with_terms
    assert user.agree_with_privacy_policy
    assert SocialAccount.objects.get(provider=GOVBR_PROVIDER_ID).user == user

    confirmation_response = client.post(confirmation_url)

    assert confirmation_response.url == "/profile/home/"
    assert client.session["_auth_user_id"] == str(user.id)


@pytest.mark.django_db
def test_govbr_registration_rejects_duplicate_email(
    client, govbr_settings, signing_key
):
    User.objects.create_user(
        "existing@example.gov.br", "password", name="Existing"
    )
    private_key, jwk = signing_key
    state, nonce = start_login(client)
    signup_response = complete_callback(
        client,
        state,
        FakeRequestsSession(
            id_token(
                govbr_settings,
                private_key,
                jwk,
                nonce,
                email_verified=False,
            ),
            {"keys": [jwk]},
        ),
    )

    response = client.post(
        signup_response.url,
        {
            "email": "existing@example.gov.br",
            "agree_with_terms": True,
            "agree_with_privacy_policy": True,
        },
    )

    assert response.status_code == 200
    assert response.context["form"].errors["email"]
    assert User.objects.count() == 1
    assert not SocialAccount.objects.filter(provider=GOVBR_PROVIDER_ID).exists()
