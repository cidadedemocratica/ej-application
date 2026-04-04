from rest_framework import viewsets, status
from rest_framework.response import Response


class RestAPIBaseViewSet(viewsets.ModelViewSet):
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except PermissionError as exc:
            return Response(
                {"error": str(exc)}, status=status.HTTP_403_FORBIDDEN
            )

    def perform_destroy(self, instance):
        self.delete_hook(self.request, instance)

    def delete_hook(self, request, instance):
        instance.delete()
