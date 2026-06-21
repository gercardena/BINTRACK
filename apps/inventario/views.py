from django.db.models import Sum

from rest_framework.views import APIView
from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.bins.models import (
    BinType,
    BinMovement,
)

from .models import Inventory
from .serializers import InventorySerializer, StockSerializer


class InventoryView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        user = request.user

        resultado = []

        bin_types = BinType.objects.all()

        for bin_type in bin_types:

            movimientos = BinMovement.objects.filter(
                usuario=user,
                bin_type=bin_type
            )

            entradas = movimientos.filter(
                tipo_movimiento="entrada"
            ).aggregate(
                total=Sum("cantidad")
            )["total"] or 0

            prestamos = movimientos.filter(
                tipo_movimiento="prestamo"
            ).aggregate(
                total=Sum("cantidad")
            )["total"] or 0

            devoluciones = movimientos.filter(
                tipo_movimiento="devolucion"
            ).aggregate(
                total=Sum("cantidad")
            )["total"] or 0

            bajas = movimientos.filter(
                tipo_movimiento="baja"
            ).aggregate(
                total=Sum("cantidad")
            )["total"] or 0

            disponible = (
                entradas
                - prestamos
                + devoluciones
                - bajas
            )

            data = {
                "bin_type_id": bin_type.id,
                "bin_nombre": bin_type.nombre,
                "entradas": entradas,
                "prestamos": prestamos,
                "devoluciones": devoluciones,
                "bajas": bajas,
                "disponible": disponible,
            }

            serializer = InventorySerializer(data)

            resultado.append(serializer.data)

        return Response(resultado)


# -------------------------------------
# Stock real por producto + bin
# GET + POST
# -------------------------------------
class StockListView(ListCreateAPIView):

    serializer_class = StockSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Inventory.objects.filter(usuario=self.request.user)

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)


# -------------------------------------
# Stock real - detalle
# GET + PUT + DELETE
# -------------------------------------
class StockDetailView(RetrieveUpdateDestroyAPIView):

    serializer_class = StockSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Inventory.objects.filter(usuario=self.request.user)