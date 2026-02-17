from rest_framework import serializers
from .models import Inventory


class InventorySerializer(serializers.ModelSerializer):

    producto_nombre = serializers.CharField(
        source="producto.nombre",
        read_only=True
    )

    class Meta:
        model = Inventory
        fields = [
            "id",
            "cliente",
            "producto",
            "producto_nombre",
            "cantidad",
            "fecha_actualizacion",
        ]
