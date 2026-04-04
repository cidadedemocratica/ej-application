import pytest
from rest_framework.test import APIClient
from ej_profiles.models import Profile
from ej_users.models import User
from ej_conversations.tests.conftest import (
    get_authorized_api_client,
    API_V1_URL,
)

PHONE_NUMBER = "61982734758"


@pytest.fixture
def superuser(db):
    superuser = User.objects.create_superuser("admin@admin.com", "admin")
    superuser.save()
    return superuser


@pytest.fixture
def api_client():
    return APIClient()


class TestGetRoutesProfile:
    def test_phone_number_endpoint(self, db, user):
        profile = user.get_profile()
        profile.phone_number = PHONE_NUMBER
        profile.save()
        api = get_authorized_api_client(
            {"email": user.email, "password": "password"}
        )
        path = API_V1_URL + "/profiles/phone-number/"
        response = api.get(path)
        assert response.status_code == 200
        response_data = response.json()
        assert response_data.get("phone_number") == PHONE_NUMBER

    def test_set_phone_number_endpoint(self, db, user):
        profile = user.get_profile()
        profile.phone_number = PHONE_NUMBER
        profile.save()
        api = get_authorized_api_client(
            {"email": user.email, "password": "password"}
        )
        path = API_V1_URL + "/profiles/set-phone-number/"
        response = api.post(path, {"phone_number": "61981178174"})
        assert response.status_code == 200
        response_data = response.json()
        assert response_data.get("phone_number") == "61981178174"

    def test_get_phone_number_endpoint_with_anonymous(self):
        api = APIClient()
        path = API_V1_URL + "/profiles/phone-number/"
        response = api.get(path)
        assert response.status_code == 401

    def test_set_phone_number_endpoint_with_anonymous(self):
        api = APIClient()
        path = API_V1_URL + "/profiles/set-phone-number/"
        response = api.post(path, {})
        assert response.status_code == 401


class TestProfileViewSet:
    def test_list_as_superuser(self, db, superuser, api_client):
        api_client.force_authenticate(user=superuser)
        response = api_client.get(API_V1_URL + "/profiles/")
        assert response.status_code == 200
        assert len(response.data) == Profile.objects.count()

    def test_list_as_regular_user(self, db, user, api_client):
        api_client.force_authenticate(user=user)
        response = api_client.get(API_V1_URL + "/profiles/")
        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]["user"] == user.id

    def test_get_object(self, db, user, api_client):
        api_client.force_authenticate(user=user)
        response = api_client.get(API_V1_URL + "/profiles/{}/".format(user.id))
        assert response.status_code == 200
        assert response.data["user"] == user.id

    def test_update_profile(self, db, user, api_client):
        api_client.force_authenticate(user=user)
        new_data = {
            "phone_number": "1234567890",
            "race": 1,
            "gender": 2,
            "birth_date": "2000-01-01",
            "region": 1,
        }
        response = api_client.put(
            API_V1_URL + "/profiles/{}/".format(user.id), new_data
        )
        assert response.status_code == 200
        assert response.data["phone_number"] == "1234567890"
        assert response.data["race"] == 1
        assert response.data["gender"] == 2
        assert response.data["birth_date"] == "2000-01-01"
        assert response.data["region"] == 1

    def test_update_profile_delete_number(self, db, user, api_client):
        api_client.force_authenticate(user=user)
        new_data = {"phone_number": ""}
        response = api_client.put(
            API_V1_URL + "/profiles/{}/".format(user.id), new_data
        )
        assert response.status_code == 200

    def test_update_profile_action(self, db, user, api_client):
        api_client.force_authenticate(user=user)
        new_data = {
            "phone_number": "0987654321",
            "race": 1,
            "gender": 1,
            "birth_date": "2000-01-01",
            "region": 2,
        }
        response = api_client.put(
            API_V1_URL + "/profiles/update_profile/", new_data
        )
        assert response.status_code == 200
        assert response.data["phone_number"] == "0987654321"
        assert response.data["race"] == 1
        assert response.data["gender"] == 1
        assert response.data["birth_date"] == "2000-01-01"
        assert response.data["region"] == 2

    def test_set_phone_number(self, db, user, api_client):
        api_client.force_authenticate(user=user)
        new_phone_number = "1234567890"
        response = api_client.post(
            API_V1_URL + "/profiles/set-phone-number/",
            {"phone_number": new_phone_number},
        )
        assert response.status_code == 200

    def test_set_phone_number_unauthenticated(self, db, api_client):
        response = api_client.post(
            API_V1_URL + "/profiles/set-phone-number/",
            {"phone_number": "1234567890"},
        )
        assert response.status_code == 401

    def test_phone_number(self, db, user, api_client):
        api_client.force_authenticate(user=user)
        response = api_client.get(API_V1_URL + "/profiles/phone-number/")
        assert response.status_code == 200

    def test_phone_number_unauthenticated(self, db, api_client):
        response = api_client.get(API_V1_URL + "/profiles/phone-number/")
        assert response.status_code == 401
