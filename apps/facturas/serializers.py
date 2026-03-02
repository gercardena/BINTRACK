from rest_framework import serializers
from .models import Factura


class FacturaSerializer(serializers.ModelSerializer):

    class Meta:
        model = Factura
        fields = "__all__"
        read_only_fields = (
            "numero",
            "subtotal",
            "iva",
            "total",
            "fecha_emision",
        )