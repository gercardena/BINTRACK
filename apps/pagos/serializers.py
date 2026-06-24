from django.db import transaction
from rest_framework import serializers

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
            "monto",
            "fecha",
        ]

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        request = self.context.get("request")

        if request and request.user.is_authenticated:
            self.fields["sale"].queryset = (
                Sale.objects.filter(
                    usuario=request.user,
                )
            )

    def validate_sale(self, sale):

        if sale.estado != "confirmed":
            raise serializers.ValidationError(
                "Solo se pueden pagar ventas confirmadas."
            )

        if sale.total <= 0:
            raise serializers.ValidationError(
                "La venta debe tener un total mayor que cero."
            )

        if Pago.objects.filter(sale=sale).exists():
            raise serializers.ValidationError(
                "La venta ya tiene un pago registrado."
            )

        return sale

    def create(self, validated_data):

        request = self.context["request"]

        selected_sale = validated_data.pop("sale")

        with transaction.atomic():

            sale = (
                Sale.objects
                .select_for_update()
                .get(
                    pk=selected_sale.pk,
                    usuario=request.user,
                )
            )

            if sale.estado != "confirmed":
                raise serializers.ValidationError({
                    "sale": (
                        "Solo se pueden pagar "
                        "ventas confirmadas."
                    )
                })

            if Pago.objects.filter(sale=sale).exists():
                raise serializers.ValidationError({
                    "sale": (
                        "La venta ya tiene "
                        "un pago registrado."
                    )
                })

            pago = Pago.objects.create(
                sale=sale,
                monto=sale.total,
                **validated_data,
            )

            sale.pay()

        return pago