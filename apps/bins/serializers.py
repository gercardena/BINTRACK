from django.db.models import Sum

from rest_framework import serializers

from .models import BinType, BinMovement
from apps.accounts.services.users import get_usuario_titular
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
            "deposito_devuelto",
            "referencia",
            "fecha",
        ]

        read_only_fields = [
            "usuario",
            "fecha",
        ]

    def validate(self, attrs):
        movement_type = attrs.get("tipo_movimiento")
        client = attrs.get("cliente")
        bin_type = attrs.get("bin_type")
        quantity = attrs.get("cantidad", 0)
        deposit_received = attrs.get("deposito_pagado", 0)
        deposit_returned = attrs.get("deposito_devuelto", 0)

        if quantity <= 0:
            raise serializers.ValidationError({
                "cantidad": "La cantidad debe ser mayor que cero.",
            })

        if movement_type in ("prestamo", "devolucion") and client is None:
            raise serializers.ValidationError({
                "cliente": "Selecciona el cliente asociado al movimiento.",
            })

        if deposit_received < 0 or deposit_returned < 0:
            raise serializers.ValidationError(
                "Los depósitos no pueden ser negativos."
            )

        if movement_type != "prestamo" and deposit_received > 0:
            raise serializers.ValidationError({
                "deposito_pagado": (
                    "La garantía recibida solo se registra en un préstamo."
                ),
            })

        if movement_type != "devolucion" and deposit_returned > 0:
            raise serializers.ValidationError({
                "deposito_devuelto": (
                    "La devolución de garantía solo se registra al devolver envases."
                ),
            })

        if movement_type == "devolucion":
            titular = get_usuario_titular(self.context["request"].user)
            movements = BinMovement.objects.filter(
                usuario=titular,
                cliente=client,
                bin_type=bin_type,
            )
            lent = movements.filter(tipo_movimiento="prestamo").aggregate(
                total=Sum("cantidad")
            )["total"] or 0
            returned = movements.filter(tipo_movimiento="devolucion").aggregate(
                total=Sum("cantidad")
            )["total"] or 0

            if quantity > lent - returned:
                raise serializers.ValidationError({
                    "cantidad": (
                        "No puedes devolver más envases de los que el cliente tiene pendientes."
                    ),
                })

            received = movements.filter(
                tipo_movimiento="prestamo",
                garantia_confirmada=True,
            ).aggregate(
                total=Sum("deposito_pagado")
            )["total"] or 0
            refunded = movements.filter(tipo_movimiento="devolucion").aggregate(
                total=Sum("deposito_devuelto")
            )["total"] or 0

            if deposit_returned > received - refunded:
                raise serializers.ValidationError({
                    "deposito_devuelto": (
                        "No puedes devolver más garantía de la que se recibió."
                    ),
                })

        return attrs

    def create(self, validated_data):
        validated_data["garantia_confirmada"] = (
            validated_data.get("deposito_pagado", 0) > 0
        )
        return super().create(validated_data)

# -------------------------------------
# Balance Serializer
# -------------------------------------
class BinBalanceSerializer(serializers.Serializer):

    cliente_id = serializers.IntegerField()

    cliente_nombre = serializers.CharField()

    bin_type_id = serializers.IntegerField()

    bin_nombre = serializers.CharField()

    valor_deposito = serializers.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    entregados = serializers.IntegerField()

    devueltos = serializers.IntegerField()

    saldo = serializers.IntegerField()

    deposito_pendiente = serializers.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    deposito_recibido = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    deposito_devuelto = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    deposito_retenido = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
