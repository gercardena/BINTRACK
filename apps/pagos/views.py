from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Pago
from .serializers import PagoSerializer


class PagoViewSet(viewsets.ModelViewSet):

    queryset = Pago.objects.all().order_by("-fecha")
    serializer_class = PagoSerializer
    permission_classes = [IsAuthenticated]
