from rest_framework import serializers
from .models import Product, ProductPresentation



class ProductSerializer(serializers.ModelSerializer):

    class Meta:
        model = Product
        fields = "__all__"
        read_only_fields = ["usuario"]  # 🔥 CLAVE
class ProductPresentationSerializer(serializers.ModelSerializer):

    product_nombre = serializers.CharField(
        source="product.nombre",
        read_only=True,
    )

    bin_nombre = serializers.CharField(
        source="bin_type.nombre",
        read_only=True,
    )

    stock = serializers.SerializerMethodField()

    class Meta:
        model = ProductPresentation

        fields = [
            "id",
            "product",
            "product_nombre",
            "bin_type",
            "bin_nombre",
            "precio",
            "activo",
            "stock",
            "fecha_creacion",
            "fecha_actualizacion",
        ]

        read_only_fields = [
            "fecha_creacion",
            "fecha_actualizacion",
        ]

    def get_stock(self, presentation):

        from apps.inventario.models import Inventory

        request = self.context.get("request")

        if request is None:
            return {
                "id": None,
                "cantidad": 0,
            }

        inventory = Inventory.objects.filter(
            usuario=request.user,
            product=presentation.product,
            bin=presentation.bin_type,
        ).first()

        if inventory is None:
            return {
                "id": None,
                "cantidad": 0,
            }

        return {
            "id": inventory.id,
            "cantidad": inventory.cantidad,
        }

    def validate_product(self, product):

        request = self.context.get("request")

        if request and product.usuario_id != request.user.id:
            raise serializers.ValidationError(
                "El producto no pertenece al usuario autenticado."
            )

        return product