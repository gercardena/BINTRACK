from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Client
from .serializers import ClientSerializer


class ClientViewSet(viewsets.ModelViewSet):

    serializer_class = ClientSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Client.objects.filter(
            usuario=self.request.user,
        )

    def perform_create(self, serializer):
        serializer.save(
            usuario=self.request.user,
        )

    def destroy(self, request, *args, **kwargs):
        client = self.get_object()

        client.activo = False
        client.save(
            update_fields=["activo"],
        )

        serializer = self.get_serializer(client)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )