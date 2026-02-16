from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated

from .models import BinType
from .serializers import BinTypeSerializer

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import Cliente, BinMovement
from .serializers import ClienteSerializer, BinMovementSerializer


# -------------------------------------
# Endpoint protegido
# GET /api/bins/types/
# -------------------------------------
class BinTypeListView(ListAPIView):

    permission_classes = [IsAuthenticated]

    serializer_class = BinTypeSerializer

    def get_queryset(self):
        return BinType.objects.all()
    
class ClienteListView(generics.ListAPIView):

    serializer_class = ClienteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Cliente.objects.filter(usuario=self.request.user)
    
class BinMovementListView(generics.ListAPIView):

    serializer_class = BinMovementSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BinMovement.objects.filter(usuario=self.request.user)