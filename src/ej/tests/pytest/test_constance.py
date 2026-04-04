import pytest
from constance.admin import Config
from constance import config

from django.contrib import admin
from ej_users.models import User


@pytest.fixture
def superuser(db):
    superuser = User.objects.create_superuser("admin@admin.com", "admin")
    superuser.save()
    return superuser


def test_config_registered_admin(superuser):
    assert admin.site.is_registered(Config)


def test_alter_ej_max_board_number_admin(client, superuser):
    client.login(email="admin@admin.com", password="admin")
    client.post(
        "/admin/constance/config/",
        {
            "version": "3764823472368",
            "EJ_MAX_BOARD_NUMBER": 2,
            "EJ_LISTEN_TO_COMMUNITY_SIGNATURE_CONVERSATIONS_LIMIT": 20,
            "EJ_LISTEN_TO_COMMUNITY_SIGNATURE_VOTE_LIMIT": 100000,
            "EJ_LISTEN_TO_CITY_SIGNATURE_CONVERSATIONS_LIMIT": 21,
            "EJ_LISTEN_TO_CITY_SIGNATURE_VOTE_LIMIT": 100000,
            "EJ_LISTEN_TO_CITY_YEARLY_SIGNATURE_VOTE_LIMIT": 1000000000,
            "EJ_LISTEN_TO_CITY_YEARLY_SIGNATURE_CONVERSATIONS_LIMIT": 1000000000,
            "EJ_PROFILE_STATE_CHOICES": "",
            "EJ_LANDING_PAGE_DOMAIN": "/login",
        },
    )
    assert config.EJ_MAX_BOARD_NUMBER == 2


# def test_required_field_admin(client, superuser):
#     client.login(email="admin@admin.com", password="admin")
#     response = client.post(
#         "/admin/constance/config/",
#         {
#             "version": "3764823472368",
#             "EJ_MAX_BOARD_NUMBER": 2,
#             "EJ_LISTEN_TO_COMMUNITY_SIGNATURE_CONVERSATIONS_LIMIT": "",
#             "EJ_LISTEN_TO_COMMUNITY_SIGNATURE_VOTE_LIMIT": 100000,
#             "EJ_LISTEN_TO_CITY_SIGNATURE_CONVERSATIONS_LIMIT": 21,
#             "EJ_LISTEN_TO_CITY_SIGNATURE_VOTE_LIMIT": 100000,
#             "EJ_LISTEN_TO_CITY_YEARLY_SIGNATURE_VOTE_LIMIT": 1000000000,
#             "EJ_LISTEN_TO_CITY_YEARLY_SIGNATURE_CONVERSATIONS_LIMIT": 1000000000,
#             "EJ_PROFILE_STATE_CHOICES": "",
#             "EJ_LANDING_PAGE_DOMAIN": "/login",
#         },
#     )
#     print(response.content)
#     assert b"errorlist" in response.content
#     assert b"This field is required." in response.content
