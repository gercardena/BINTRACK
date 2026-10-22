from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.services.users import get_usuario_titular
from apps.ventas.models import Sale

from .models import Factura, FacturaCambio
from .serializers import FacturaSerializer, FacturaEdicionSerializer, FacturaCambioSerializer


class FacturaViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = FacturaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        titular = get_usuario_titular(
            self.request.user,
        )

        return (
            Factura.objects
            .filter(
                sale__usuario=titular,
            )
            .select_related(
                "sale",
                "sale__cliente",
            )
        )

    @action(detail=True, methods=["post"])
    def editar(self, request, pk=None):
        with transaction.atomic():
            # Filter by titular before locking; never accept an owner from the client.
            factura = get_object_or_404(
                self.get_queryset().select_for_update(of=("self",)), pk=pk,
            )
            self.check_object_permissions(request, factura)
            serializer = FacturaEdicionSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = dict(serializer.validated_data)
            version = data.pop("version")
            if version != factura.version:
                return Response(
                    {"detail": "El comprobante cambió. Vuelve a abrirlo antes de editar."},
                    status=status.HTTP_409_CONFLICT,
                )
            cambios = {
                campo: {"antes": getattr(factura, campo), "despues": valor}
                for campo, valor in data.items() if getattr(factura, campo) != valor
            }
            if cambios:
                for campo in cambios:
                    setattr(factura, campo, data[campo])
                factura.version += 1
                factura.save(update_fields=[*cambios, "version"])
                FacturaCambio.objects.create(
                    factura=factura, usuario=request.user,
                    usuario_nombre=request.user.get_username(), cambios=cambios,
                )
            return Response(self.get_serializer(factura).data)

    @action(detail=True, methods=["get"])
    def historial(self, request, pk=None):
        factura = self.get_object()
        return Response(FacturaCambioSerializer(factura.cambios.all(), many=True).data)

    @action(detail=True, methods=["post"])
    def generar(self, request, pk=None):

        titular = get_usuario_titular(
            request.user,
        )

        with transaction.atomic():

            try:
                sale = (
                    Sale.objects
                    .select_for_update()
                    .select_related("cliente")
                    .get(
                        pk=pk,
                        usuario=titular,
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
