from rest_framework import serializers
from .models import RasaConversation, OpinionComponent


class RasaConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = RasaConversation
        fields = ["conversation", "domain"]


class OpinionComponentSerializer(serializers.ModelSerializer):
    class Meta:
        model = OpinionComponent
        fields = ["final_voting_message"]

    def to_representation(self, instance: OpinionComponent):
        """
        to_representation customizes how Serializers returns data
        """

        return {
            "final_voting_message": instance.final_voting_message,
        }

    def get_empty_data(request):
        return {
            "final_voting_message": "",
        }
