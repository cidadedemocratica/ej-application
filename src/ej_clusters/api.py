from ej_clusters.models.clusterization import Clusterization
from ej_conversations.models import Conversation
from sidekick import import_later
from rest_framework.decorators import action
from rest_framework.response import Response
from ej.viewsets import RestAPIBaseViewSet
from .utils import cluster_shapes
from ej_clusters.serializers import (
    ClusterizationSerializer,
    ClusterSerializer,
    StereotypeSerializer,
)
from ej.permissions import IsOwner, IsSuperUser
from rest_framework.permissions import IsAdminUser

math = import_later(".math", package=__package__)


class ClusterizationViewSet(RestAPIBaseViewSet):
    queryset = Clusterization.objects.all()
    serializer_class = ClusterizationSerializer
    permission_classes = [IsOwner, IsSuperUser, IsAdminUser]

    def list(self, request):
        if request.user.is_superuser:
            queryset = Clusterization.objects.all()
        else:
            conversation = Conversation.objects.filter(author=request.user)
            queryset = Clusterization.objects.filter(
                conversation__in=conversation
            )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True)
    def clusters(self, request, pk):
        clusterization = self.get_object()
        clusters = clusterization.clusters.all()
        serializer = ClusterSerializer(
            clusters, context={"request": request}, many=True
        )
        return Response(serializer.data)

    @action(detail=True)
    def affinities(self, request, pk):
        clusterization = self.get_object()
        shapes = cluster_shapes(clusterization, user=request.user)
        return Response(shapes)

    @action(detail=True)
    def stereotypes(self, request, pk):
        clusterization = self.get_object()
        serializer = StereotypeSerializer(
            clusterization.stereotypes.all(),
            context={"request": request},
            many=True,
        )
        return Response(serializer.data)
