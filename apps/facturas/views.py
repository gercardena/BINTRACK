from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction

from .models import Factura
from .serializers import FacturaSerializer
from apps.ventas.models import Sale


class FacturaViewSet(viewsets.ModelViewSet):
    queryset = Factura.objects.all()
    serializer_class = FacturaSerializer

    @action(detail=True, methods=["post"])
    def generar(self, request, pk=None):

        sale = Sale.objects.get(pk=pk)

        # Validaciones
        if sale.estado != "paid":
            return Response(
                {"error": "Solo se puede facturar una venta pagada."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if sale.facturada:
            return Response(
                {"error": "Esta venta ya está facturada."},
                status=status.HTTP_400_BAD_REQUEST,
            )

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

            sale.facturada = True
            sale.save()

        serializer = self.get_serializer(factura)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
