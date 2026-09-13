from rest_framework import serializers

from .models import Factura


class FacturaItemSerializer(serializers.Serializer):
    product_nombre = serializers.CharField()
    bin_nombre = serializers.CharField()
    cantidad = serializers.IntegerField()
    bins_cantidad = serializers.IntegerField()
    tipo_cobro = serializers.CharField()
    kilos_pesados = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        allow_null=True,
    )
    precio_unitario = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    subtotal = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
    )


class FacturaSerializer(serializers.ModelSerializer):
    sale_numero = serializers.CharField(
        source="sale.numero",
        read_only=True,
    )

    sale_estado = serializers.CharField(
        source="sale.estado",
        read_only=True,
    )

    items = serializers.SerializerMethodField()

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
            "items",
        ]

        read_only_fields = fields

    def get_items(self, factura):
        sale_items = (
            factura.sale.items
            .select_related(
                "product",
                "bin",
            )
            .all()
        )

        data = []

        for item in sale_items:
            data.append({
                "product_nombre": item.product.nombre,
                "bin_nombre": item.bin.nombre,
                "cantidad": item.cantidad,
                "bins_cantidad": item.bins_cantidad,
                "tipo_cobro": item.tipo_cobro_snapshot,
                "kilos_pesados": item.kilos_pesados,
                "precio_unitario": item.precio_unitario,
                "subtotal": item.subtotal,
            })

        serializer = FacturaItemSerializer(
            data,
            many=True,
        )

        return serializer.data