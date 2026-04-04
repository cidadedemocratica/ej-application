from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from django.http import Http404
from ej.permissions import IsAuthenticatedOnlyGetView
from .models import Board
from .serializers import BoardDetailSerializer, BoardSerializer
from ej_conversations.serializers import BoardConversationSerializer
from ej_conversations.models.conversation import Conversation


class BoardViewSet(viewsets.ModelViewSet):
    queryset = Board.objects.all()
    serializer_class = BoardSerializer
    permission_classes = [IsAuthenticatedOnlyGetView]

    def retrieve(self, request, pk):
        board = self.get_object()
        return Response(BoardDetailSerializer(board).data)

    @action(detail=True, url_path="conversations/(?P<conversation_id>\d+)")
    def conversations(self, request, pk, conversation_id):
        try:
            conversation = Conversation.objects.get(
                id=conversation_id, board__id=pk
            )
            serializer = BoardConversationSerializer(
                conversation, context={"request": request}
            )
            return Response(serializer.data)
        except Conversation.DoesNotExist:
            raise Http404
