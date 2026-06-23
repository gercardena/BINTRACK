from django.db.models import Sum
from rest_framework import serializers

from apps.bins.models import BinMovement
from apps.productos.models import ProductPresentation

from .models import Inventory


class InventorySerializer(serializers.Serializer):

    bin_type_id = serializers.IntegerField()
    bin_nombre = serializers.CharField()

    entradas = serializers.IntegerField()
    prestamos = serializers.IntegerField()
    devoluciones = serializers.IntegerField()
    bajas = serializers.IntegerField()

    en_clientes = serializers.IntegerField()
    llenos = serializers.IntegerField()
    disponible = serializers.IntegerField()


class StockSerializer(serializers.ModelSerializer):

    product_nombre = serializers.CharField(
        source="product.nombre",
        read_only=True,
    )

    bin_nombre = serializers.CharField(
        source="bin.nombre",
        read_only=True,
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

        read_only_fields = [
            "usuario",
            "fecha_creacion",
            "fecha_actualizacion",
        ]

    def validate(self, attrs):

        request = self.context["request"]
        user = request.user

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

        if cantidad < 0:
            raise serializers.ValidationError({
                "cantidad": "La cantidad no puede ser negativa."
            })

        if product.usuario_id != user.id:
            raise serializers.ValidationError({
                "product": "El producto no pertenece al usuario."
            })

        presentation_exists = ProductPresentation.objects.filter(
            product=product,
            bin_type=bin_type,
            activo=True,
        ).exists()

        if not presentation_exists:
            raise serializers.ValidationError({
                "bin": (
                    "No existe una presentación activa para "
                    "este producto y tipo de envase."
                )
            })

        movimientos = BinMovement.objects.filter(
            usuario=user,
            bin_type=bin_type,
        )

        entradas = movimientos.filter(
            tipo_movimiento="entrada",
        ).aggregate(
            total=Sum("cantidad"),
        )["total"] or 0

        prestamos = movimientos.filter(
            tipo_movimiento="prestamo",
        ).aggregate(
            total=Sum("cantidad"),
        )["total"] or 0

        devoluciones = movimientos.filter(
            tipo_movimiento="devolucion",
        ).aggregate(
            total=Sum("cantidad"),
        )["total"] or 0

        bajas = movimientos.filter(
            tipo_movimiento="baja",
        ).aggregate(
            total=Sum("cantidad"),
        )["total"] or 0

        en_clientes = prestamos - devoluciones

        capacidad_para_llenos = (
            entradas
            - bajas
            - en_clientes
        )

        otros_inventarios = Inventory.objects.filter(
            usuario=user,
            bin=bin_type,
        )

        if self.instance:
            otros_inventarios = otros_inventarios.exclude(
                pk=self.instance.pk
            )

        llenos_otros_productos = otros_inventarios.aggregate(
            total=Sum("cantidad"),
        )["total"] or 0

        maximo_permitido = (
            capacidad_para_llenos
            - llenos_otros_productos
        )

        if cantidad > maximo_permitido:
            raise serializers.ValidationError({
                "cantidad": (
                    f"Solo hay {maximo_permitido} envases "
                    "disponibles para esta presentación."
                )
            })

        return attrs