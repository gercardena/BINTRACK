from decimal import Decimal

from django.db.models import Sum

from rest_framework.generics import ListCreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import BinType, BinMovement
from .serializers import (
    BinTypeSerializer,
    ClienteSerializer,
    BinMovementSerializer,
    BinBalanceSerializer
)

from apps.clientes.models import Client


# -------------------------------------
# Tipos de envase
# GET + POST
# -------------------------------------
class BinTypeListView(ListCreateAPIView):

    permission_classes = [IsAuthenticated]
    serializer_class = BinTypeSerializer

    def get_queryset(self):
        return BinType.objects.all()


# -------------------------------------
# Clientes bins
# GET + POST
# -------------------------------------
class ClienteListView(ListCreateAPIView):

    serializer_class = ClienteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):

        return Client.objects.all()

    def perform_create(self, serializer):

        serializer.save()


# -------------------------------------
# Movimientos
# GET + POST
# -------------------------------------
class BinMovementListView(ListCreateAPIView):

    serializer_class = BinMovementSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):

        return BinMovement.objects.filter(
            usuario=self.request.user
        )

    def perform_create(self, serializer):

        serializer.save(
            usuario=self.request.user
        )


# -------------------------------------
# Balance por cliente
# -------------------------------------
class BinBalanceView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        user = request.user

        clientes = Client.objects.all()

        resultado = []

        for cliente in clientes:

            movimientos = BinMovement.objects.filter(
                usuario=user,
                cliente=cliente
            )

            entregados = movimientos.filter(
                tipo_movimiento="prestamo"
            ).aggregate(
                total=Sum("cantidad")
            )["total"] or 0

            devueltos = movimientos.filter(
                tipo_movimiento="devolucion"
            ).aggregate(
                total=Sum("cantidad")
            )["total"] or 0

            saldo = entregados - devueltos

            deposito_total = Decimal("0.00")

            for m in movimientos:

                deposito_total += (
                    m.cantidad *
                    m.bin_type.valor_deposito
                )

            data = {
                "cliente_id": cliente.id,
                "cliente_nombre": cliente.nombre,
                "entregados": entregados,
                "devueltos": devueltos,
                "saldo": saldo,
                "deposito_pendiente": deposito_total,
            }

            serializer = BinBalanceSerializer(data)

            resultado.append(serializer.data)

        return Response(resultado)