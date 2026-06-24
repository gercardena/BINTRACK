from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Pago
from .serializers import PagoSerializer


class PagoViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):

    serializer_class = PagoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Pago.objects
            .filter(
                sale__usuario=self.request.user,
            )
            .select_related(
                "sale",
                "sale__cliente",
            )
        )
