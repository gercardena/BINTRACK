from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.services.users import get_usuario_titular

from .models import Client
from .serializers import ClientSerializer


class ClientViewSet(viewsets.ModelViewSet):
    serializer_class = ClientSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        titular = get_usuario_titular(
            self.request.user,
        )

        return Client.objects.filter(
            usuario=titular,
        )

    def perform_create(self, serializer):
        titular = get_usuario_titular(
            self.request.user,
        )

        serializer.save(
            usuario=titular,
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