from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import Inventory
from .serializers import InventorySerializer


class InventoryListView(generics.ListAPIView):

    permission_classes = [IsAuthenticated]
    serializer_class = InventorySerializer

    def get_queryset(self):
        return Inventory.objects.all()
