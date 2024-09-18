from datetime import datetime
from io import BytesIO
import random as rd
import string as s

from PIL import Image

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.utils import NotSupportedError
from django.test import Client, RequestFactory
from django.urls import reverse
from ej.testing import UrlTester
from ej_conversations.models import Conversation
from ej_profiles import enums
from ej_profiles.views import HomeView
from ej_users.models import User
import pytest


class TestRoutes(UrlTester):
    user_urls = ["/profile/", "/profile/edit/"]


def create_image(filename, size=(100, 100), image_mode="RGB", image_format="png"):
    data = BytesIO()
    Image.new(image_mode, size).save(data, image_format)
    data.name = filename
    data.seek(0)
    return data


@pytest.fixture
def logged_client(db):
    user = User.objects.create_user("email@server.com", "password")
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def test_user(db):
    return User.objects.create_user("test_user@email.br", "password")


@pytest.fixture
def test_user_board(test_user):
    return User.create_user_default_board(test_user)


@pytest.fixture
def promoted_conversation(test_user, test_user_board):
    return Conversation.objects.create(
        title="promoted", author=test_user, is_promoted=True, board=test_user_board
    )


class TestEditProfile:
    def test_user_logged_access_edit_profile(self, logged_client):
        resp = logged_client.get("/profile/edit/")
        assert resp.status_code == 200

    def test_user_logged_edit_profile_picture(self, logged_client):
        avatar = create_image("avatar.png")
        avatar_file = SimpleUploadedFile("front.png", avatar.getvalue())
        form_data = {
            "name": "Maurice",
            "profile_photo": avatar_file,
            "gender": 0,
            "race": 0,
        }

        response = logged_client.post("/profile/edit/", form_data)
        assert response.status_code == 302 and response.url == "/profile/"
        user = User.objects.get(email="email@server.com")
        assert user.profile.profile_photo.name

    def test_user_logged_edit_profile_basic_info(self, logged_client):
        def rand_str(size):
            return "".join(rd.choices(s.ascii_lowercase, k=size))

        def gen_birth_date():
            return f"{rd.randint(1900, 2020)}-{rd.randint(1, 12)}-" f"{rd.randint(1, 28)}"

        inf_fields = [
            "name",
            "city",
            "occupation",
            "country",
            "ethnicity",
            "education",
            "political_activity",
            "biography",
            "state",
            "gender",
            "race",
            "birth_date",
        ]
        inf_values = [
            *[rand_str(15)] * 8,
            "DF",
            int(rd.choice(list(enums.Gender))),
            int(rd.choice(list(enums.Race))),
            gen_birth_date(),
        ]
        form_data = {k: v for k, v in zip(inf_fields, inf_values)}

        response = logged_client.post("/profile/edit/", form_data)
        assert (
            response.status_code == 302 and response.url == "/profile/"
        ), f"Error found using post message {form_data}"
        user = User.objects.get(email="email@server.com")

        for attr in ["gender", "race"]:
            assert getattr(user.profile, attr) == form_data[attr]
            inf_fields.remove(attr)
        assert (
            user.profile.birth_date
            == datetime.strptime(form_data["birth_date"], "%Y-%m-%d").date()
        )
        inf_fields.remove("birth_date")

        blacklist = settings.EJ_PROFILE_EXCLUDE_FIELDS
        for attr in inf_fields:
            if attr not in blacklist:
                assert getattr(user.profile, attr) == form_data[attr], attr

    def test_change_password(self, logged_client):
        response = logged_client.post(
            "/profile/",
            {
                "current_password": "password",
                "password": "newpassword",
                "password_confirm": "newpassword",
            },
        )
        assert response.status_code == 200
        assert response.wsgi_request.user.check_password("newpassword")

    def test_change_password_wrong_current_password(self, logged_client):
        response = logged_client.post(
            "/profile/",
            {
                "current_password": "wrongpassword",
                "password": "newpassword",
                "password_confirm": "newpassword",
            },
        )
        assert response.status_code == 200
        assert b"Incorrect current password" in response.content
        assert not response.wsgi_request.user.check_password("newpassword")

    def test_change_password_wrong_repeat_password(self, logged_client):
        response = logged_client.post(
            "/profile/",
            {
                "current_password": "password",
                "password": "newpassword",
                "password_confirm": "wrongpassword",
            },
        )
        assert response.status_code == 200
        assert b"Passwords do not match" in response.content
        assert not response.wsgi_request.user.check_password("newpassword")


class TestTour:
    def test_redirect_if_tour_is_incomplete(self, test_user):
        url = "/profile/home/"
        client = Client()
        client.force_login(test_user)

        response = client.get(url)

        assert response.status_code == 302
        assert response.url == "/profile/tour/"

    def test_redirect_after_skip_tour(self, test_user):
        url = "/profile/tour/?step=skip"
        client = Client()
        client.force_login(test_user)
        response = client.post(url)
        assert response.status_code == 302
        assert response["HX-Redirect"] == reverse("profile:home")

    def test_redirect_after_tour_completion(self, test_user):
        url = "/profile/tour/?step=end"
        client = Client()
        client.force_login(test_user)
        response = client.post(url)
        assert response.status_code == 302
        assert response["HX-Redirect"] == reverse("profile:home")


class TestHome:
    def test_home_not_compatible_with_test_db(self, test_user, promoted_conversation):
        profile = test_user.get_profile()
        profile.completed_tour = True
        profile.save()
        factory = RequestFactory()
        request = factory.get("/profile/home")
        request.user = test_user
        with pytest.raises(NotSupportedError):
            # DISTINCT not supported by test db sqlite
            HomeView.as_view()(request)
