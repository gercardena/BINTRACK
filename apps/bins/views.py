from django.db.models import Sum

from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.services.users import get_usuario_titular
from apps.clientes.models import Client

from .models import BinType, BinMovement
from .serializers import (
    BinTypeSerializer,
    ClienteSerializer,
    BinMovementSerializer,
    BinBalanceSerializer,
)


# -------------------------------------
# Tipos de envase
# GET + POST
# -------------------------------------
class BinTypeListView(ListCreateAPIView):

    permission_classes = [IsAuthenticated]
    serializer_class = BinTypeSerializer

    def get_queryset(self):
        titular = get_usuario_titular(
            self.request.user,
        )

        return BinType.objects.filter(
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
# Tipo de envase detalle
# GET + PUT + DELETE
# -------------------------------------
class BinTypeDetailView(RetrieveUpdateDestroyAPIView):

    serializer_class = BinTypeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        titular = get_usuario_titular(
            self.request.user,
        )

        return BinType.objects.filter(
            usuario=titular,
        )


# -------------------------------------
# Clientes bins
# GET + POST
# -------------------------------------
class ClienteListView(ListCreateAPIView):

    serializer_class = ClienteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        titular = get_usuario_titular(
            self.request.user,
        )

        return Client.objects.filter(
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
# Cliente detalle
# GET + PUT + DELETE
# -------------------------------------
class ClienteDetailView(RetrieveUpdateDestroyAPIView):

    serializer_class = ClienteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        titular = get_usuario_titular(
            self.request.user,
        )

        return Client.objects.filter(
            usuario=titular,
        )


# -------------------------------------
# Movimientos
# GET + POST
# -------------------------------------
class BinMovementListView(ListCreateAPIView):

    serializer_class = BinMovementSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        titular = get_usuario_titular(
            self.request.user,
        )

        return BinMovement.objects.filter(
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
# Balance por cliente
# -------------------------------------
class BinBalanceView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        titular = get_usuario_titular(
            request.user,
        )

        resultado = []

        clientes = Client.objects.filter(
            usuario=titular,
        )

        bin_types = BinType.objects.filter(
            usuario=titular,
        )

        for cliente in clientes:

            for bin_type in bin_types:

                movimientos = BinMovement.objects.filter(
                    usuario=titular,
                    cliente=cliente,
                    bin_type=bin_type,
                )

                if not movimientos.exists():
                    continue

                entregados = movimientos.filter(
                    tipo_movimiento="prestamo",
                ).aggregate(
                    total=Sum("cantidad"),
                )["total"] or 0

                devueltos = movimientos.filter(
                    tipo_movimiento="devolucion",
                ).aggregate(
                    total=Sum("cantidad"),
                )["total"] or 0

                saldo = entregados - devueltos

                deposito_pendiente = (
                    saldo *
                    bin_type.valor_deposito
                )

                data = {
                    "cliente_id": cliente.id,
                    "cliente_nombre": cliente.nombre,

                    "bin_type_id": bin_type.id,
                    "bin_nombre": bin_type.nombre,
                    "valor_deposito": bin_type.valor_deposito,

                    "entregados": entregados,
                    "devueltos": devueltos,
                    "saldo": saldo,

                    "deposito_pendiente":
                        deposito_pendiente,
                }

                serializer = BinBalanceSerializer(
                    data,
                )

                resultado.append(
                    serializer.data,
                )

        return Response(resultado)