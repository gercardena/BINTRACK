from rest_framework import serializers
from .models import Sale, SaleItem


# =========================================
# 🔹 SALE ITEM SERIALIZER
# =========================================

class SaleItemSerializer(serializers.ModelSerializer):

    product_nombre = serializers.CharField(
        source="product.nombre",
        read_only=True
    )

    bin_nombre = serializers.CharField(
        source="bin.nombre",
        read_only=True
    )

    class Meta:
        model = SaleItem

        fields = [
            "id",

            # 🔥 IMPORTANTE
            "sale",

            "product",
            "product_nombre",

            "bin",
            "bin_nombre",

            "cantidad",

            "bins_cantidad",

            "precio_unitario",

            "subtotal",
        ]


# =========================================
# 🔹 SALE SERIALIZER
# =========================================

class SaleSerializer(serializers.ModelSerializer):

    items = SaleItemSerializer(many=True, read_only=True)

    cliente_nombre = serializers.CharField(
        source="cliente.nombre",
        read_only=True
    )

    class Meta:
        model = Sale

        fields = [
            "id",
            "numero",
            "estado",
            "cliente",
            "cliente_nombre",
            "subtotal",
            "iva",
            "total",
            "items",
            "fecha_creacion",
        ]