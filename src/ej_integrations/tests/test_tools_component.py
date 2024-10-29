from io import BytesIO
from PIL import Image
from django.test import Client
from django.core.files.base import File

from ej_conversations.mommy_recipes import ConversationRecipes
from ej_integrations.models import OpinionComponent

ConversationRecipes.update_globals(globals())


class TestOpinionComponent(ConversationRecipes):
    @staticmethod
    def get_image_file(name, ext="png", size=(50, 50), color=(256, 0, 0)):
        file_obj = BytesIO()
        image = Image.new("RGBA", size=size, color=color)
        image.save(file_obj, ext)
        file_obj.seek(0)
        return File(file_obj, name=name)

    def test_custom_conversation_component_without_mandatory_fields(
        self, conversation_db
    ):
        client = Client()
        client.force_login(conversation_db.author)

        url = conversation_db.patch_url("conversation-tools:opinion-component")
        data = {
            "conversation": conversation_db.id,
            "final_voting_message": "finished voting!",
        }
        response = client.post(url, data)
        assert response.status_code == 302
        assert not OpinionComponent.objects.filter(conversation=conversation_db).exists()

    def test_get_conversation_component(self, conversation_db):
        client = Client()
        client.force_login(conversation_db.author)

        url = conversation_db.patch_url("conversation-tools:opinion-component")
        response = client.get(url)
        assert response.status_code == 200
