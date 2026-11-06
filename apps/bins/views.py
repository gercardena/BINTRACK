from django.db.models import Q, Sum

from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.services.users import get_usuario_titular
from apps.accounts.permissions.subscription import HasActiveSubscription
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

    permission_classes = [IsAuthenticated, HasActiveSubscription]
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
    permission_classes = [IsAuthenticated, HasActiveSubscription]

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
    permission_classes = [IsAuthenticated, HasActiveSubscription]

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
    permission_classes = [IsAuthenticated, HasActiveSubscription]

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
    permission_classes = [IsAuthenticated, HasActiveSubscription]

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

    permission_classes = [IsAuthenticated, HasActiveSubscription]

    def get(self, request):

        titular = get_usuario_titular(
            request.user,
        )

        cliente_id = request.query_params.get("cliente")
        bin_type_id = request.query_params.get("bin_type")
        solo_pendientes = (
            request.query_params.get("solo_pendientes", "false").lower()
            in ("true", "1", "yes")
        )

        try:
            if cliente_id:
                cliente_id = int(cliente_id)
            if bin_type_id:
                bin_type_id = int(bin_type_id)
        except ValueError:
            return Response(
                {"detail": "Los filtros cliente y bin_type deben ser numéricos."},
                status=400,
            )

        movimientos = BinMovement.objects.filter(
            usuario=titular,
            cliente__isnull=False,
        )
        if cliente_id:
            movimientos = movimientos.filter(cliente_id=cliente_id)
        if bin_type_id:
            movimientos = movimientos.filter(bin_type_id=bin_type_id)

        grupos = movimientos.values(
            "cliente_id",
            "cliente__nombre",
            "bin_type_id",
            "bin_type__nombre",
            "bin_type__valor_deposito",
        ).annotate(
            entregados=Sum("cantidad", filter=Q(tipo_movimiento="prestamo")),
            devueltos=Sum("cantidad", filter=Q(tipo_movimiento="devolucion")),
        ).order_by("cliente__nombre", "bin_type__nombre")

        resultado = []
        for grupo in grupos:
            entregados = grupo["entregados"] or 0
            devueltos = grupo["devueltos"] or 0
            saldo = entregados - devueltos

            if solo_pendientes and saldo <= 0:
                continue

            data = {
                "cliente_id": grupo["cliente_id"],
                "cliente_nombre": grupo["cliente__nombre"],
                "bin_type_id": grupo["bin_type_id"],
                "bin_nombre": grupo["bin_type__nombre"],
                "valor_deposito": grupo["bin_type__valor_deposito"],
                "entregados": entregados,
                "devueltos": devueltos,
                "saldo": saldo,
                "deposito_pendiente": saldo * grupo["bin_type__valor_deposito"],
            }
            resultado.append(BinBalanceSerializer(data).data)

        return Response(resultado)
