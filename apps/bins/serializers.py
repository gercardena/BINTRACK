from rest_framework import serializers

from .models import BinType, BinMovement
from apps.clientes.models import Client


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
        model = Client
        fields = "__all__"
        read_only_fields = ["usuario"]


# -------------------------------------
# BinMovement
# -------------------------------------
class BinMovementSerializer(serializers.ModelSerializer):

    cliente_nombre = serializers.CharField(
        source="cliente.nombre",
        read_only=True
    )

    bin_nombre = serializers.CharField(
        source="bin_type.nombre",
        read_only=True
    )

    class Meta:
        model = BinMovement

        fields = [
            "id",
            "usuario",
            "cliente",
            "cliente_nombre",
            "bin_type",
            "bin_nombre",
            "tipo_movimiento",
            "cantidad",
            "deposito_pagado",
            "referencia",
            "fecha",
        ]

        read_only_fields = [
            "usuario",
            "fecha",
        ]


# -------------------------------------
# Balance Serializer
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