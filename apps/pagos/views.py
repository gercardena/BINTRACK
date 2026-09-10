from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from apps.accounts.services.users import get_usuario_titular

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
        titular = get_usuario_titular(
            self.request.user,
        )

        return (
            Pago.objects
            .filter(
                sale__usuario=titular,
            )
            .select_related(
                "sale",
                "sale__cliente",
            )
        )