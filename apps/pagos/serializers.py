from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from rest_framework import serializers

from apps.accounts.services.users import get_usuario_titular
from apps.ventas.models import Sale

from .models import Pago


class PagoSerializer(serializers.ModelSerializer):
    sale = serializers.PrimaryKeyRelatedField(
        queryset=Sale.objects.none(),
    )

    sale_numero = serializers.CharField(
        source="sale.numero",
        read_only=True,
    )

    cliente_nombre = serializers.CharField(
        source="sale.cliente.nombre",
        read_only=True,
    )

    class Meta:
        model = Pago

        fields = [
            "id",
            "sale",
            "sale_numero",
            "cliente_nombre",
            "monto",
            "metodo",
            "referencia",
            "fecha",
        ]

        read_only_fields = [
            "fecha",
        ]

        extra_kwargs = {
            "monto": {
                "required": False,
            },
        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        request = self.context.get("request")

        if request and request.user.is_authenticated:
            titular = get_usuario_titular(
                request.user,
            )

            self.fields["sale"].queryset = (
                Sale.objects.filter(
                    usuario=titular,
                )
            )

    def validate_sale(self, sale):

        if sale.estado not in ["confirmed", "partial"]:
            raise serializers.ValidationError(
                "Solo se pueden registrar abonos en ventas confirmadas."
            )

        if sale.total <= 0:
            raise serializers.ValidationError(
                "La venta debe tener un total mayor que cero."
            )

        return sale

    def validate(self, attrs):
        attrs = super().validate(attrs)
        monto = attrs.get("monto")

        if monto is not None and monto <= 0:
            raise serializers.ValidationError({
                "monto": "El abono debe ser mayor que cero.",
            })

        return attrs

    def create(self, validated_data):

        request = self.context["request"]

        titular = get_usuario_titular(
            request.user,
        )

        selected_sale = validated_data.pop("sale")

        with transaction.atomic():

            sale = (
                Sale.objects
                .select_for_update()
                .get(
                    pk=selected_sale.pk,
                    usuario=titular,
                )
            )

            if sale.estado not in ["confirmed", "partial"]:
                raise serializers.ValidationError({
                    "sale": (
                        "Solo se pueden registrar abonos "
                        "en ventas confirmadas."
                    )
                })

            total_pagado = Pago.objects.filter(
                sale=sale,
            ).aggregate(total=Sum("monto"))["total"] or Decimal("0.00")

            saldo_pendiente = sale.total - total_pagado
            monto = validated_data.get("monto") or saldo_pendiente

            if monto > saldo_pendiente:
                raise serializers.ValidationError({
                    "monto": "El abono no puede superar el saldo pendiente.",
                })

            validated_data["monto"] = monto

            pago = Pago.objects.create(
                sale=sale,
                **validated_data,
            )

            sale.actualizar_estado_pago(
                total_pagado + pago.monto,
            )

        return pago
