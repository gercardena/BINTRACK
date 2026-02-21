from rest_framework import serializers
from .models import Inventory


class InventorySerializer(serializers.ModelSerializer):

    product_nombre = serializers.CharField(
        source="product.nombre",
        read_only=True
    )

    bin_nombre = serializers.CharField(
        source="bin.nombre",
        read_only=True
    )

    class Meta:
        model = Inventory
        fields = [
            "id",
            "product",
            "product_nombre",
            "bin",
            "bin_nombre",
            "cantidad",
            "fecha_creacion",
            "fecha_actualizacion",
        ]

