from django.test import Client
from ej_users.models import User
from ej_users.mommy_recipes import UserRecipes


class TestUserView(UserRecipes):
    def test_invalid_login(self, db, rf, anonymous_user):
        credentials = {"email": "random_email@server.com", "password": "1234"}
        client = Client()
        response = client.post("/login/", credentials)
        assert response.context["form"].errors

    def test_successful_login(self, user_client, user_db):
        user_db.set_password("1234")
        credentials = {"email": user_db.email, "password": "1234"}
        user_client.post("/login/", data=credentials)
        assert user_client.session["_auth_user_id"] == str(user_db.pk)

    def test_logout(self, user_client):
        assert "_auth_user_id" in user_client.session
        user_client.post("/account/logout/")
        assert "_auth_user_id" not in user_client.session

    def test_register_valid_user(self, client, db):
        response = client.post(
            "/register/",
            data={
                "name": "Turanga Leela",
                "email": "leela@example.com",
                "password": "pass123",
                "password_confirm": "pass123",
                "agree_with_terms": True,
                "agree_with_privacy_policy": True,
            },
        )
        user = User.objects.get(email="leela@example.com")
        assert client.session["_auth_user_id"] == str(user.pk)
        assert response.url == "/profile/home/"
        response = client.get("/profile/home/")
        assert response.url == "/profile/tour/"

    def test_recover_user_password(self, db, user, client):
        user.save()
        response = client.post("/recover-password/", data={"email": user.email})

        # Fetch token url and go to token page saving new password
        token_url = response.context[0]["url"].partition("/testserver")[2]
        client.post(token_url, data={"password": "12345", "password_confirm": "12345"})

        client.login(email=user.email, password="12345")
        assert client.session["_auth_user_id"] == str(user.pk)

    def test_remove_account(self, user_client, user_db):
        client, user = user_client, user_db
        client.post("/account/remove/", data={"confirm": "true", "email": user.email})
        updated_user = User.objects.get(id=user.id)
        assert updated_user.email.endswith("@deleted-account")

    def test_register_invalid_email(self, client, db):
        User.objects.create_user("name@server.com", "1234", name="name")

        response = client.post(
            "/register/",
            data={
                "name": "Turanga Leela",
                "email": "name@server.com",
                "password": "pass123",
                "password_confirm": "pass123",
                "agree_with_terms": True,
                "agree_with_privacy_policy": True,
            },
        )

        assert response.status_code == 200
        assert b"User with this Email address already exists." in response.content

    def test_register_unmatch_passwords(self, client, db):
        response = client.post(
            "/register/",
            data={
                "name": "Turanga Leela",
                "email": "name@server.com",
                "password": "password",
                "password_confirm": "anotherpassword",
                "agree_with_terms": True,
                "agree_with_privacy_policy": True,
            },
        )

        assert response.status_code == 200
        assert b"Passwords do not match" in response.content
