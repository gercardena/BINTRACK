from rest_framework import serializers

from .models import Factura, FacturaCambio


class FacturaEdicionSerializer(serializers.Serializer):
    version = serializers.IntegerField(min_value=0)
    cliente_nombre = serializers.CharField(max_length=255, required=False)
    cliente_direccion = serializers.CharField(max_length=255, allow_blank=True, required=False)
    observaciones = serializers.CharField(max_length=2000, allow_blank=True, required=False)

    def to_internal_value(self, data):
        if not isinstance(data, dict):
            raise serializers.ValidationError("Se esperaba un objeto de datos.")
        extra = set(data) - set(self.fields)
        if extra:
            raise serializers.ValidationError({key: "Este campo no se puede editar." for key in extra})
        return super().to_internal_value(data)


class FacturaCambioSerializer(serializers.ModelSerializer):
    class Meta:
        model = FacturaCambio
        fields = ["id", "usuario_nombre", "fecha", "cambios"]
        read_only_fields = fields


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
            "observaciones",
            "version",
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
