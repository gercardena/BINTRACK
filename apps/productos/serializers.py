from rest_framework import serializers

from .models import Product, ProductPresentation


class ProductSerializer(serializers.ModelSerializer):

    class Meta:
        model = Product
        fields = "__all__"
        read_only_fields = ["usuario"]


class ProductPresentationSerializer(
    serializers.ModelSerializer
):

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

    def validate(self, attrs):

        request = self.context.get("request")

        product = attrs.get(
            "product",
            getattr(self.instance, "product", None),
        )

        bin_type = attrs.get(
            "bin_type",
            getattr(self.instance, "bin_type", None),
        )

        activo = attrs.get(
            "activo",
            getattr(self.instance, "activo", True),
        )

        if request and activo is False:

            from apps.inventario.models import Inventory

            cantidad = Inventory.objects.filter(
                usuario=request.user,
                product=product,
                bin=bin_type,
            ).values_list(
                "cantidad",
                flat=True,
            ).first() or 0

            if cantidad > 0:
                raise serializers.ValidationError({
                    "activo": (
                        "No puedes desactivar una presentación "
                        "que todavía tiene stock."
                    )
                })

        return attrs

    def validate_product(self, product):

        request = self.context.get("request")

        if request and product.usuario_id != request.user.id:
            raise serializers.ValidationError(
                "El producto no pertenece al usuario autenticado."
            )

        return product