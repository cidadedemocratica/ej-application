import pytest
from ej_conversations.enums import Choice
from ej_users.models import User
from ej_conversations.tests.conftest import API_V1_URL
from rest_framework.test import APIClient
from enum import Enum


class UserType(Enum):
    ANONYMOUS = "anonymous"
    AUTH = "auth"
    COMPLETED_REGISTRATION = "auth_linked"
    ANOTHER_AUTH_LINKED = "another_auth_linked"


class UserFake:
    OFFICIAL_PASSWORD = "OiPNMcJ£]£]A4_>N,Ng@dx~s>?XCb^4E'idea5HHVvJ8:IP5"
    USERS = {
        UserType.ANONYMOUS: {
            "name": "anonymous user",
            "email": "anonymous@mail.com",
            "password": OFFICIAL_PASSWORD,
            "password_confirm": OFFICIAL_PASSWORD,
            "has_completed_registration": False,
        },
        UserType.AUTH: {
            "name": "Auth User",
            "email": "auth.user@mail.com",
            "password": "pass123@123",
            "password_confirm": "pass123@123",
            "has_completed_registration": False,
        },
        UserType.COMPLETED_REGISTRATION: {
            "email": "auth.user@mail.com",
            "password": OFFICIAL_PASSWORD,
        },
        UserType.ANOTHER_AUTH_LINKED: {
            "name": "Another User",
            "email": "another.user@mail.com",
            "password": OFFICIAL_PASSWORD,
            "password_confirm": OFFICIAL_PASSWORD,
            "has_completed_registration": False,
        },
    }


class EJRequests:
    def __init__(self, client):
        self.client = client

    def get_token(self, user_type: UserType, secret_id=None):
        user = UserFake.USERS[user_type]
        data = {
            "email": user["email"],
            "password": user["password"],
        }

        if secret_id:
            data["secret_id"] = secret_id
        else:
            data.pop("secret_id", None)

        response = self.client.post(
            API_V1_URL + "/token/",
            data=data,
            content_type="application/json",
        )

        if response.status_code != 200:
            response_data = response.json()
            raise Exception(response_data)

        assert response.status_code == 200

        response_data = response.json()
        return response_data["access_token"]

    def create_user(self, user_type: UserType, secret_id=None):
        user = UserFake.USERS[user_type]
        data = user

        if secret_id:
            data["secret_id"] = secret_id
        else:
            data.pop("secret_id", None)

        response = self.client.post(
            API_V1_URL + "/users/",
            data=data,
            content_type="application/json",
        )

        return response

    def get_user(self, user_type: UserType, token):
        user = UserFake.USERS[user_type]
        email = user["email"]
        response = self.client.get(
            API_V1_URL + f"/users/{email}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        return response

    def update_user(self, user_type: UserType, secret_id):
        user = UserFake.USERS[user_type]
        data = {"email": user["email"], "password": user["password"]}

        response = self.client.put(
            API_V1_URL + f"/users/{secret_id}/",
            data=data,
            content_type="application/json",
        )
        return response

    def delete_user(self, email, token):
        response = self.client.delete(
            API_V1_URL + f"/users/{email}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        return response

    def get_users(self, token):
        response = self.client.get(
            API_V1_URL + "/users/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        return response


class TestUserAPI:

    SECRET_ID = (
        "8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92"
    )

    def test_generate_access_token(self, db, user):
        api = APIClient()
        response = api.post(
            API_V1_URL + "/token/",
            {"email": user.email, "password": "password"},
            format="json",
        )
        data = response.json()
        assert response.status_code == 200
        assert data["access_token"]
        assert data["refresh_token"]

    def test_refresh_token(self, db, user):
        api = APIClient()
        response = api.post(
            API_V1_URL + "/token/",
            {"email": user.email, "password": "password"},
            format="json",
        )
        data = response.json()
        old_access_token = data["access_token"]
        refresh_token = data["refresh_token"]
        response = api.post(
            API_V1_URL + "/refresh-token/",
            {"refresh": refresh_token},
            format="json",
        )
        data = response.json()
        assert data["access"]
        assert data["access"] != old_access_token

    def test_registration_auth_valid_user(self, client, db):
        client.post(
            API_V1_URL + "/users/",
            data={
                "name": "David Silva",
                "email": "david@example.com",
                "password": "pass123",
                "password_confirm": "pass123",
            },
            content_type="application/json",
        )
        user = User.objects.get(email="david@example.com")
        assert user.name == "David Silva"
        assert user.email == "david@example.com"

    def test_registration_rest_auth_incorrect_confirm_password(
        self, client, db
    ):
        response = client.post(
            API_V1_URL + "/users/",
            data={
                "name": "jonatas Silva",
                "email": "jonatassilva@example.com",
                "password": "pass123",
                "password_confirm": "pass1234",
            },
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_registration_rest_auth_missing_password(self, client, db):
        response = client.post(
            API_V1_URL + "/users/",
            data={
                "name": "jonatas Silva",
                "email": "jonatasgomes@mail.com",
                "password_confirm": "pass123",
            },
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_user_endpoint_post_with_already_created_user(self, client, db):
        User.objects.create_user("user@user.com", "password")
        response = client.post(
            API_V1_URL + "/users/",
            data={
                "email": "user@user.com",
            },
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_merge_users_with_empty_votes(
        self, client, db, conversation, user, another_user
    ):
        comment_1 = conversation.create_comment(
            another_user, "my comment 1", "approved"
        )
        comment_2 = conversation.create_comment(
            another_user, "my comment 2", "approved"
        )
        comment_3 = conversation.create_comment(
            another_user, "my comment 3", "approved"
        )
        comment_4 = conversation.create_comment(
            another_user, "my comment 4", "approved"
        )
        comment_1.vote(author=another_user, choice=Choice.DISAGREE)
        comment_2.vote(author=another_user, choice=Choice.DISAGREE)
        comment_3.vote(author=another_user, choice=Choice.AGREE)
        comment_4.vote(author=another_user, choice=Choice.SKIP)
        user = User.objects.merge_users(another_user, user)
        assert user.votes.all().count() == 4
        with pytest.raises(Exception):
            User.objects.get(id=another_user.id)

    def test_merge_users_with_equal_votes(
        self, client, db, conversation, user, another_user
    ):
        comment_1 = conversation.create_comment(
            another_user, "my comment 1", "approved"
        )
        comment_2 = conversation.create_comment(
            another_user, "my comment 2", "approved"
        )
        comment_3 = conversation.create_comment(
            another_user, "my comment 3", "approved"
        )
        comment_1.vote(author=another_user, choice=Choice.DISAGREE)
        comment_2.vote(author=another_user, choice=Choice.DISAGREE)
        comment_1.vote(author=user, choice=Choice.AGREE)
        comment_3.vote(author=user, choice=Choice.AGREE)
        user = User.objects.merge_users(another_user, user)
        assert user.votes.all().count() == 3
        assert user.votes.get(comment__id=comment_1.id).choice == Choice.AGREE
        with pytest.raises(Exception):
            User.objects.get(id=another_user.id)

    def test_create_users_with_null_secret_id(self, client, db):
        response = client.post(
            API_V1_URL + "/users/",
            data={
                "name": "tester 1",
                "email": "tester1@example.com",
                "password": "pass123",
                "password_confirm": "pass123",
            },
            content_type="application/json",
        )

        assert response.status_code == 201
        assert not User.objects.get(email="tester1@example.com").secret_id

        response = client.post(
            API_V1_URL + "/users/",
            data={
                "name": "tester 2",
                "email": "tester2@example.com",
                "password": "pass123",
                "password_confirm": "pass123",
            },
            content_type="application/json",
        )
        assert response.status_code == 201
        assert not User.objects.get(email="tester2@example.com").secret_id

    def test_get_token_after_user_registration(self, client, db):
        response = client.post(
            API_V1_URL + "/users/",
            data={
                "name": "tester",
                "email": "tester@example.com",
                "password": "pass123",
                "password_confirm": "pass123",
            },
            content_type="application/json",
        )
        assert response.json()["access_token"]
        assert response.status_code == 201

    def test_missing_credentials_in_login_should_return_error(self, client, db):
        User.objects.create_user("user@user.com", "password")
        response = client.post(
            API_V1_URL + "/users/",
            data={
                "email": "user@user.com",
            },
            content_type="application/json",
        )
        assert response.status_code == 400

        response = client.post(
            API_V1_URL + "/login/",
            data={"password": "password"},
            content_type="application/json",
        )
        assert response.status_code == 400

        response = client.post(
            API_V1_URL + "/login/",
            data={"email": "user@user.com", "password": ""},
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_get_token_after_user_login(self, client, db):
        User.objects.create_user("user@user.com", "password")
        response = client.post(
            "/api/v1/login/",
            data={"email": "user@user.com", "password": "password"},
            content_type="application/json",
        )

        assert response.json()["access_token"]
        assert response.status_code == 200

    def test_create_user_with_secret_id(self, client, db):
        ej_requests = EJRequests(client)

        response = ej_requests.create_user(
            UserType.AUTH, secret_id=TestUserAPI.SECRET_ID
        )
        assert response.status_code == 201

        user = User.objects.get(email=UserFake.USERS[UserType.AUTH]["email"])
        assert user.name == UserFake.USERS[UserType.AUTH]["name"]
        assert user.email == UserFake.USERS[UserType.AUTH]["email"]

    def test_user_has_completed_the_registration(self, client, db):
        ej_requests = EJRequests(client)

        # Create anonymous user
        response = ej_requests.create_user(
            UserType.ANONYMOUS, secret_id=TestUserAPI.SECRET_ID
        )
        assert response.status_code == 201

        # Create auth user
        response = ej_requests.create_user(UserType.AUTH)
        assert response.status_code == 201

        # Send request to merge users
        response = ej_requests.update_user(
            UserType.COMPLETED_REGISTRATION, TestUserAPI.SECRET_ID
        )
        assert response.status_code == 200

        user = User.objects.get(
            secret_id=User.encode_secret_id(TestUserAPI.SECRET_ID)
        )
        assert user.name == UserFake.USERS[UserType.AUTH]["name"]
        assert user.email == UserFake.USERS[UserType.AUTH]["email"]
        assert user.secret_id == User.encode_secret_id(TestUserAPI.SECRET_ID)
        assert user.has_completed_registration

        with pytest.raises(User.DoesNotExist):
            user = User.objects.get(
                email=UserFake.USERS[UserType.ANONYMOUS]["email"]
            )

    def test_get_token_by_email_and_password(self, client, db):
        ej_requests = EJRequests(client)

        response = ej_requests.create_user(
            UserType.ANONYMOUS, secret_id=TestUserAPI.SECRET_ID
        )
        assert response.status_code == 201

        access_token = ej_requests.get_token(UserType.ANONYMOUS)
        assert access_token

    def test_get_token_by_email_and_password_after_complete_registration(
        self, client, db
    ):
        ej_requests = EJRequests(client)

        # Create whatsapp user
        response = ej_requests.create_user(
            UserType.ANONYMOUS, secret_id=TestUserAPI.SECRET_ID
        )
        assert response.status_code == 201

        # Create regular user
        response = ej_requests.create_user(UserType.AUTH)
        assert response.status_code == 201

        # Merge WhatsApp user with Regular user
        response = ej_requests.update_user(
            UserType.COMPLETED_REGISTRATION, TestUserAPI.SECRET_ID
        )
        assert response.status_code == 200

        # WhatsApp user request a new token
        access_token = ej_requests.get_token(
            UserType.ANONYMOUS, secret_id=TestUserAPI.SECRET_ID
        )

        assert access_token

    def test_user_try_linked_to_auth_user(self, client, db):
        ej_requests = EJRequests(client)

        # Create anonymous user
        response = ej_requests.create_user(
            UserType.ANONYMOUS, secret_id=TestUserAPI.SECRET_ID
        )
        assert response.status_code == 201

        # Create auth user
        response = ej_requests.create_user(UserType.AUTH)
        assert response.status_code == 201

        # Link secret_id to auth user
        response = ej_requests.update_user(
            UserType.COMPLETED_REGISTRATION, TestUserAPI.SECRET_ID
        )
        assert response.status_code == 200

        # Create another user
        response = ej_requests.create_user(UserType.ANOTHER_AUTH_LINKED)
        assert response.status_code == 201

        response = ej_requests.update_user(
            UserType.ANOTHER_AUTH_LINKED, TestUserAPI.SECRET_ID
        )
        assert response.status_code == 403

    def test_external_service_try_to_update_nonexistent_user(self, client, db):
        ej_requests = EJRequests(client)

        response = ej_requests.update_user(
            UserType.COMPLETED_REGISTRATION, TestUserAPI.SECRET_ID
        )
        assert response.status_code == 404

    def test_external_service_try_to_request_token_for_nonexistent_user(
        self, client, db
    ):
        response = client.post(
            API_V1_URL + "/token/",
            data={
                "email": "noexistentuser@mail.com",
                "password": "invalidpassword",
            },
            content_type="application/json",
        )
        assert response.status_code == 404
