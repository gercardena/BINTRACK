from django.db import transaction
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.ventas.models import Sale

from .models import Factura
from .serializers import FacturaSerializer


class FacturaViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):

    serializer_class = FacturaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Factura.objects
            .filter(
                sale__usuario=self.request.user,
            )
            .select_related(
                "sale",
                "sale__cliente",
            )
        )

    @action(detail=True, methods=["post"])
    def generar(self, request, pk=None):

        with transaction.atomic():

            try:
                sale = (
                    Sale.objects
                    .select_for_update()
                    .select_related("cliente")
                    .get(
                        pk=pk,
                        usuario=request.user,
                    )
                )

            except Sale.DoesNotExist:
                return Response(
                    {
                        "error": (
                            "Venta no encontrada."
                        )
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            if sale.estado not in [
                "confirmed",
                "paid",
            ]:
                return Response(
                    {
                        "error": (
                            "Solo se pueden facturar "
                            "ventas confirmadas o pagadas."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            factura_existente = (
                Factura.objects
                .filter(sale=sale)
                .first()
            )

            if factura_existente is not None:
                serializer = self.get_serializer(
                    factura_existente,
                )

                return Response(
                    serializer.data,
                    status=status.HTTP_200_OK,
                )

            if not sale.items.exists():
                return Response(
                    {
                        "error": (
                            "No se puede facturar "
                            "una venta sin artículos."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if sale.total <= 0:
                return Response(
                    {
                        "error": (
                            "No se puede facturar "
                            "una venta con total cero."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            factura = Factura.objects.create(
                sale=sale,
                numero=f"F{sale.id:04d}",
                cliente_nombre=(
                    sale.cliente.nombre
                ),
                cliente_rut=sale.cliente.rut,
                cliente_direccion=(
                    sale.cliente.direccion
                ),
                subtotal=sale.subtotal,
                iva=sale.iva,
                total=sale.total,
            )

        serializer = self.get_serializer(
            factura,
        )

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )