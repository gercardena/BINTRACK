from rest_framework import serializers

from .models import Factura


class FacturaSerializer(serializers.ModelSerializer):

    sale_numero = serializers.CharField(
        source="sale.numero",
        read_only=True,
    )

    sale_estado = serializers.CharField(
        source="sale.estado",
        read_only=True,
    )

    class Meta:
        model = Factura

        fields = [
            "id",
            "sale",
            "sale_numero",
            "sale_estado",
            "numero",
            "cliente_nombre",
            "cliente_rut",
            "cliente_direccion",
            "subtotal",
            "iva",
            "total",
            "fecha_emision",
        ]

        read_only_fields = fields