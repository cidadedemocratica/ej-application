from urllib.parse import urlencode

import pytest
from allauth.socialaccount.models import SocialAccount
from django.urls import reverse

from ej_users.models import User
from ej_govbr.constants import GOVBR_AUTHENTICATED_SESSION_KEY


@pytest.mark.django_db
def test_govbr_button_is_hidden_when_disabled(client, settings):
    settings.GOVBR_ENABLED = False

    login_response = client.get("/login/")
    registration_response = client.get("/register/")

    assert b'id="govbr-button"' not in login_response.content
    assert b'id="govbr-button"' not in registration_response.content


@pytest.mark.django_db
def test_govbr_button_is_shown_on_login_and_registration_pages(
    client, settings
):
    settings.GOVBR_ENABLED = True

    login_response = client.get("/login/?next=/profile/home/")
    registration_response = client.get("/register/?next=/profile/home/")

    expected_href = b"/accounts/govbr/login/?next=%2Fprofile%2Fhome%2F"
    assert b'id="govbr-button"' in login_response.content
    assert b"<strong>GOV.BR</strong>" in login_response.content
    assert expected_href in login_response.content
    assert b'id="govbr-button"' in registration_response.content
    assert b"<strong>GOV.BR</strong>" in registration_response.content
    assert expected_href in registration_response.content


@pytest.mark.django_db
def test_govbr_logout_clears_the_local_session_and_redirects(client, settings):
    user = User.objects.create_user("citizen@example.gov.br", "password")
    client.force_login(user)
    session = client.session
    session[GOVBR_AUTHENTICATED_SESSION_KEY] = True
    session.save()
    settings.GOVBR_LOGOUT_URL = "https://sso.example.gov.br/logout"
    settings.GOVBR_POST_LOGOUT_REDIRECT_URI = "https://ej.example.gov.br/"

    response = client.post(reverse("account:logout"))

    expected_query = urlencode(
        {"post_logout_redirect_uri": settings.GOVBR_POST_LOGOUT_REDIRECT_URI}
    )
    assert response.url == f"{settings.GOVBR_LOGOUT_URL}?{expected_query}"
    assert "_auth_user_id" not in client.session
    assert GOVBR_AUTHENTICATED_SESSION_KEY not in client.session


@pytest.mark.django_db
def test_google_logout_remains_local(client):
    user = User.objects.create_user("citizen@example.gov.br", "password")
    SocialAccount.objects.create(
        user=user, provider="google", uid="google-user"
    )
    client.force_login(user)

    response = client.post(reverse("account:logout"))

    assert response.status_code == 200
    assert "_auth_user_id" not in client.session
