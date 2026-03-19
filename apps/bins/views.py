from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics

from django.db.models import Sum

from rest_framework.views import APIView
from rest_framework.response import Response

from .models import BinType, Cliente, BinMovement
from .serializers import (
    BinTypeSerializer,
    ClienteSerializer,
    BinMovementSerializer,
    BinBalanceSerializer
)
from decimal import Decimal

# -------------------------------------
# Tipos de envase
# -------------------------------------
class BinTypeListView(ListAPIView):

    permission_classes = [IsAuthenticated]
    serializer_class = BinTypeSerializer

    def get_queryset(self):
        return BinType.objects.all()


# -------------------------------------
# Clientes
# -------------------------------------
class ClienteListView(generics.ListAPIView):

    serializer_class = ClienteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Cliente.objects.filter(usuario=self.request.user)


# -------------------------------------
# Movimientos
# -------------------------------------
class BinMovementListView(generics.ListAPIView):

    serializer_class = BinMovementSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BinMovement.objects.filter(usuario=self.request.user)


# -------------------------------------
# 🔥 NUEVO: Balance por cliente
# -------------------------------------
class BinBalanceView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        user = request.user

        clientes = Cliente.objects.filter(usuario=user)

        resultado = []

        for cliente in clientes:

            movimientos = BinMovement.objects.filter(
                usuario=user,
                cliente=cliente
            )

            # 🔹 SUMAS
            entregados = movimientos.filter(
                tipo_movimiento="prestamo"
            ).aggregate(total=Sum("cantidad"))["total"] or 0

            devueltos = movimientos.filter(
                tipo_movimiento="devolucion"
            ).aggregate(total=Sum("cantidad"))["total"] or 0

            saldo = entregados - devueltos

            # 🔹 DEPÓSITO (simple)
            deposito_total = Decimal("0.00")

            for m in movimientos:
                deposito_total += m.cantidad * m.bin_type.valor_deposito

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