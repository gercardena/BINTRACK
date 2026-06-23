from rest_framework import serializers

from apps.productos.models import ProductPresentation

from .models import Sale, SaleItem


# =========================================
# SALE ITEM SERIALIZER
# =========================================

class SaleItemSerializer(serializers.ModelSerializer):

    product_nombre = serializers.CharField(
        source="product.nombre",
        read_only=True,
    )

    bin_nombre = serializers.CharField(
        source="bin.nombre",
        read_only=True,
    )

    class Meta:
        model = SaleItem

        fields = [
            "id",
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

        read_only_fields = [
            "bins_cantidad",
            "precio_unitario",
            "subtotal",
        ]

    def validate(self, attrs):

        request = self.context["request"]
        user = request.user

        sale = attrs.get(
            "sale",
            getattr(self.instance, "sale", None),
        )

        product = attrs.get(
            "product",
            getattr(self.instance, "product", None),
        )

        bin_type = attrs.get(
            "bin",
            getattr(self.instance, "bin", None),
        )

        cantidad = attrs.get(
            "cantidad",
            getattr(self.instance, "cantidad", 0),
        )

        if sale.usuario_id != user.id:
            raise serializers.ValidationError(
                "La venta no pertenece al usuario autenticado."
            )

        if sale.estado != "draft":
            raise serializers.ValidationError(
                "Solo se pueden modificar ventas en borrador."
            )

        if product.usuario_id != user.id:
            raise serializers.ValidationError(
                "El producto no pertenece al usuario autenticado."
            )

        if cantidad < 1:
            raise serializers.ValidationError({
                "cantidad": "La cantidad debe ser mayor que cero."
            })

        try:
            presentation = ProductPresentation.objects.get(
                product=product,
                bin_type=bin_type,
                activo=True,
            )

        except ProductPresentation.DoesNotExist:
            raise serializers.ValidationError({
                "bin": (
                    "No existe una presentación activa para "
                    "este producto y envase."
                )
            })

        # El backend determina estos valores.
        attrs["precio_unitario"] = presentation.precio
        attrs["bins_cantidad"] = cantidad

        return attrs


# =========================================
# SALE SERIALIZER
# =========================================

class SaleSerializer(serializers.ModelSerializer):

    items = SaleItemSerializer(
        many=True,
        read_only=True,
    )

    cliente_nombre = serializers.CharField(
        source="cliente.nombre",
        read_only=True,
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