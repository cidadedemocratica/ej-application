from rest_framework.test import APIClient
from rest_framework.reverse import reverse


class TestOpinionComponentViewSet:
    def test_request_empty_configuration(self, db, client):
        api = APIClient()
        endpoint = reverse("v1-opinion-component-detail", kwargs={"pk": 0})
        response = api.get(endpoint)
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["final_voting_message"] == ""

    def test_request_configuration(self, db, client, custom_request, opinion_component):
        api = APIClient()
        final_voting_message = opinion_component.final_voting_message
        endpoint = reverse(
            "v1-opinion-component-detail",
            kwargs={"pk": opinion_component.conversation.id},
        )
        response = api.get(endpoint)
        response_data = response.json()
        assert response.status_code == 200
        assert response_data["final_voting_message"] == final_voting_message
