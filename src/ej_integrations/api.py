from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated

from ej_conversations.models import Conversation
from ej_integrations.serializers import (
    RasaConversationSerializer,
    OpinionComponentSerializer,
)
from .models import RasaConversation, OpinionComponent


class OpinionComponentViewSet(viewsets.ViewSet):
    """
    OpinionComponentViewSet exposes OpinionComponent configuration on API.
    This View is consumed mainly by OpinionComponent tool.
    """

    permission_classes = []
    serializer_class = OpinionComponentSerializer

    def retrieve(self, request, pk):
        try:
            conversation = Conversation.objects.get(id=pk)
            opinion_component = OpinionComponent.objects.get(conversation=conversation)
            serializer = OpinionComponentSerializer(
                opinion_component, context={"request": request}
            )
            return Response(serializer.data)
        except Exception:
            return Response(OpinionComponentSerializer.get_empty_data(request))


class RasaConversationViewSet(viewsets.ModelViewSet):
    queryset = RasaConversation.objects.all()
    serializer_class = RasaConversationSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request):
        if request.user.is_superuser:
            queryset = RasaConversation.objects.all()
        else:
            conversation = Conversation.objects.filter(author=request.user)
            queryset = RasaConversation.objects.filter(conversation__in=conversation)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    #
    # Rasa connector
    # usage: api/v1/rasa-conversations/integrations?domain=URL
    #
    @action(detail=False, permission_classes=[AllowAny])
    def integrations(self, request):
        domain = request.GET.get("domain")
        try:
            integration = RasaConversation.objects.get(domain=domain)
            response = {
                "conversation": {
                    "id": integration.conversation.id,
                    "title": integration.conversation.text,
                    "text": integration.conversation.text,
                },
                "domain": integration.domain,
            }
            return Response(response)
        except RasaConversation.DoesNotExist:
            return Response({}, status=200)
