from rest_framework import serializers
from .models import BinType, Cliente, BinMovement


# -------------------------------------
# BinType
# -------------------------------------
class BinTypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = BinType
        fields = "__all__"


# -------------------------------------
# Cliente
# -------------------------------------
class ClienteSerializer(serializers.ModelSerializer):

    class Meta:
        model = Cliente
        fields = "__all__"


# -------------------------------------
# Movimientos
# -------------------------------------
class BinMovementSerializer(serializers.ModelSerializer):

    class Meta:
        model = BinMovement
        fields = "__all__"


# -------------------------------------
# 🔥 NUEVO: Balance por cliente
# -------------------------------------
class BinBalanceSerializer(serializers.Serializer):

    cliente_id = serializers.IntegerField()
    cliente_nombre = serializers.CharField()

    entregados = serializers.IntegerField()
    devueltos = serializers.IntegerField()
    saldo = serializers.IntegerField()

    deposito_pendiente = serializers.DecimalField(
        max_digits=12,
        decimal_places=2
    )