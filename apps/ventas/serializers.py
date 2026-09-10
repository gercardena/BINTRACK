from rest_framework import serializers

from apps.accounts.services.users import get_usuario_titular
from apps.productos.models import ProductPresentation

from .models import Sale, SaleItem


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
            "tipo_cobro_snapshot",
            "kilos_pesados",
            "precio_unitario",
            "subtotal",
        ]

        read_only_fields = [
            "bins_cantidad",
            "subtotal",
        ]

    def validate(self, attrs):

        request = self.context["request"]
        titular = get_usuario_titular(
            request.user,
        )

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

        tipo_cobro = attrs.get(
            "tipo_cobro_snapshot",
            getattr(
                self.instance,
                "tipo_cobro_snapshot",
                "envase",
            ),
        )

        kilos_pesados = attrs.get(
            "kilos_pesados",
            getattr(self.instance, "kilos_pesados", None),
        )

        if sale.usuario_id != titular.id:
            raise serializers.ValidationError(
                "La venta no pertenece al usuario titular."
            )

        if sale.estado != "draft":
            raise serializers.ValidationError(
                "Solo se pueden modificar ventas en borrador."
            )

        if product.usuario_id != titular.id:
            raise serializers.ValidationError(
                "El producto no pertenece al usuario titular."
            )

        if cantidad < 1:
            raise serializers.ValidationError({
                "cantidad": (
                    "La cantidad debe ser mayor que cero."
                )
            })

        if tipo_cobro not in ["envase", "kilo"]:
            raise serializers.ValidationError({
                "tipo_cobro_snapshot": (
                    "Tipo de cobro inválido."
                )
            })

        try:
            presentation = ProductPresentation.objects.get(
                product=product,
                bin_type=bin_type,
                tipo_cobro=tipo_cobro,
                activo=True,
            )

        except ProductPresentation.DoesNotExist:
            raise serializers.ValidationError({
                "bin": (
                    "No existe una presentación activa para "
                    "este producto, envase y tipo de cobro."
                )
            })

        precio_unitario = attrs.get(
            "precio_unitario",
            getattr(self.instance, "precio_unitario", None),
        )

        if precio_unitario is None or precio_unitario <= 0:
            precio_unitario = presentation.precio

        attrs["precio_unitario"] = precio_unitario
        attrs["bins_cantidad"] = cantidad
        attrs["tipo_cobro_snapshot"] = presentation.tipo_cobro

        if presentation.tipo_cobro == "kilo":
            if kilos_pesados is None or kilos_pesados <= 0:
                raise serializers.ValidationError({
                    "kilos_pesados": (
                        "Debes ingresar los kilos pesados "
                        "para esta presentación."
                    )
                })
        else:
            attrs["kilos_pesados"] = None

        return attrs


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

        read_only_fields = [
            "numero",
            "estado",
            "subtotal",
            "iva",
            "total",
            "fecha_creacion",
        ]

    def validate_cliente(self, cliente):

        request = self.context.get("request")

        if request:
            titular = get_usuario_titular(
                request.user,
            )

            if cliente.usuario_id != titular.id:
                raise serializers.ValidationError(
                    "El cliente no pertenece al "
                    "usuario titular."
                )

        if not cliente.activo:
            raise serializers.ValidationError(
                "No se puede utilizar un cliente inactivo."
            )

        return cliente