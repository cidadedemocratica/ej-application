from rest_framework import serializers
from rest_framework.reverse import reverse
from .models import Board

from ej_conversations.serializers import BoardConversationSerializer


class BoardSerializer(serializers.ModelSerializer):
    owner = serializers.SlugRelatedField(read_only=True, slug_field="email")
    links = serializers.SerializerMethodField()

    class Meta:
        model = Board
        fields = ["title", "slug", "owner", "description", "links"]

    def get_links(self, obj):
        return {
            "self": reverse(
                "v1-boards-detail",
                args=[obj.id],
                request=self.context["request"],
            ),
        }


class BoardDetailSerializer(BoardSerializer):
    conversations = BoardConversationSerializer(
        source="conversation_set", many=True
    )

    class Meta:
        model = Board
        fields = ["title", "slug", "owner", "description", "conversations"]
