from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from django.db import transaction

from apps.ventas.models import Sale
from .models import Factura
from .serializers import FacturaSerializer


class FacturaViewSet(viewsets.ModelViewSet):

    queryset = Factura.objects.all()

    serializer_class = FacturaSerializer

    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=["post"])
    def generar(self, request, pk=None):

        try:
            sale = Sale.objects.get(
                pk=pk,
                usuario=request.user
            )

        except Sale.DoesNotExist:

            return Response(
                {
                    "error": "Venta no encontrada."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # =====================================
        # VALIDAR ESTADO
        # =====================================

        if sale.estado != "paid":

            return Response(
                {
                    "error": "Solo se puede facturar una venta pagada."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # =====================================
        # VALIDAR FACTURA EXISTENTE
        # =====================================

        if hasattr(sale, "factura"):

            return Response(
                {
                    "error": "Esta venta ya está facturada."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # =====================================
        # VALIDAR ITEMS
        # =====================================

        if not sale.items.exists():

            return Response(
                {
                    "error": "No se puede facturar una venta sin items."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # =====================================
        # VALIDAR TOTAL
        # =====================================

        if sale.total <= 0:

            return Response(
                {
                    "error": "No se puede facturar una venta con total 0."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # =====================================
        # CREAR FACTURA
        # =====================================

        with transaction.atomic():

            numero = f"F{sale.id:04d}"

            factura = Factura.objects.create(

                sale=sale,

                numero=numero,

                cliente_nombre=sale.cliente.nombre,

                cliente_rut=sale.cliente.rut,

                cliente_direccion=sale.cliente.direccion,

                subtotal=sale.subtotal,

                iva=sale.iva,

                total=sale.total,
            )

        serializer = self.get_serializer(factura)

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )