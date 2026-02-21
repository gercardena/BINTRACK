from rest_framework import generics, permissions
from .models import Inventory
from .serializers import InventorySerializer


class InventoryListView(generics.ListAPIView):

    serializer_class = InventorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Inventory.objects.filter(usuario=self.request.user)

