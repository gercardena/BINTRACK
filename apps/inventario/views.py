from django.db.models import Sum

from rest_framework.views import APIView
from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.accounts.services.users import get_usuario_titular
from apps.bins.models import (
    BinType,
    BinMovement,
)

from .models import Inventory
from .serializers import InventorySerializer, StockSerializer


class InventoryView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        titular = get_usuario_titular(
            request.user,
        )

        resultado = []

        bin_types = BinType.objects.filter(
            usuario=titular,
        )

        for bin_type in bin_types:

            movimientos = BinMovement.objects.filter(
                usuario=titular,
                bin_type=bin_type,
            )

            entradas = movimientos.filter(
                tipo_movimiento="entrada",
            ).aggregate(
                total=Sum("cantidad"),
            )["total"] or 0

            prestamos = movimientos.filter(
                tipo_movimiento="prestamo",
            ).aggregate(
                total=Sum("cantidad"),
            )["total"] or 0

            devoluciones = movimientos.filter(
                tipo_movimiento="devolucion",
            ).aggregate(
                total=Sum("cantidad"),
            )["total"] or 0

            bajas = movimientos.filter(
                tipo_movimiento="baja",
            ).aggregate(
                total=Sum("cantidad"),
            )["total"] or 0

            # Envases llenos con productos disponibles para vender
            llenos = Inventory.objects.filter(
                usuario=titular,
                bin=bin_type,
            ).aggregate(
                total=Sum("cantidad"),
            )["total"] or 0

            # Envases que todavía permanecen con clientes
            en_clientes = prestamos - devoluciones

            # Envases vacíos disponibles para volver a cargar
            disponible = (
                entradas
                - bajas
                - en_clientes
                - llenos
            )

            data = {
                "bin_type_id": bin_type.id,
                "bin_nombre": bin_type.nombre,
                "entradas": entradas,
                "prestamos": prestamos,
                "devoluciones": devoluciones,
                "bajas": bajas,
                "en_clientes": en_clientes,
                "llenos": llenos,
                "disponible": disponible,
            }

            serializer = InventorySerializer(data)
            resultado.append(serializer.data)

        return Response(resultado)


# -------------------------------------
# Stock real por producto + envase
# GET + POST
# -------------------------------------
class StockListView(ListCreateAPIView):

    serializer_class = StockSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        titular = get_usuario_titular(
            self.request.user,
        )

        return Inventory.objects.filter(
            usuario=titular,
        )

    def perform_create(self, serializer):
        titular = get_usuario_titular(
            self.request.user,
        )

        serializer.save(
            usuario=titular,
        )


# -------------------------------------
# Stock real - detalle
# GET + PUT + DELETE
# -------------------------------------
class StockDetailView(RetrieveUpdateDestroyAPIView):

    serializer_class = StockSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        titular = get_usuario_titular(
            self.request.user,
        )

        return Inventory.objects.filter(
            usuario=titular,
        )