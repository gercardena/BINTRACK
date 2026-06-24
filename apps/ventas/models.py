from django.db import models, transaction
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Max, Sum
from decimal import Decimal

from apps.productos.models import Product
from apps.inventario.models import Inventory
from apps.bins.models import BinMovement, BinType


IVA_RATE = Decimal("0.19")


# =========================================
# 🔹 INVENTORY MOVEMENT
# =========================================

class InventoryMovement(models.Model):

    MOVEMENT_TYPES = [
        ("in", "Entrada"),
        ("out", "Salida"),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    bin = models.ForeignKey("bins.BinType", on_delete=models.CASCADE)

    tipo = models.CharField(max_length=10, choices=MOVEMENT_TYPES)
    cantidad = models.PositiveIntegerField()

    referencia = models.CharField(max_length=50)

    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.tipo} - {self.product.nombre} ({self.cantidad})"


# =========================================
# 🔹 SALE
# =========================================

class Sale(models.Model):

    STATUS_CHOICES = [
        ("draft", "Borrador"),
        ("confirmed", "Confirmada"),
        ("paid", "Pagada"),
        ("cancelled", "Cancelada"),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sales"
    )

    cliente = models.ForeignKey(
        "clientes.Client",
        on_delete=models.PROTECT,
        related_name="sales"
    )

    numero = models.CharField(max_length=20, unique=True, blank=True)

    estado = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft"
    )

    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    iva = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return f"Venta {self.numero}"

    def generar_numero(self):
        ultimo = Sale.objects.aggregate(Max("id"))["id__max"]
        siguiente = (ultimo or 0) + 1
        return f"V{siguiente:04d}"

    def save(self, *args, **kwargs):
        if not self.numero:
            self.numero = self.generar_numero()
        super().save(*args, **kwargs)

    def calcular_totales(self):
        items = self.items.all()
        subtotal = sum((item.subtotal for item in items), Decimal("0.00"))
        iva = subtotal * IVA_RATE
        total = subtotal + iva

        self.subtotal = subtotal
        self.iva = iva
        self.total = total

        super().save(update_fields=["subtotal", "iva", "total"])

    # =========================================
    # 🔹 CONFIRMAR VENTA
    # =========================================

    def confirm(self):

     with transaction.atomic():

        # Bloquea la venta para evitar confirmarla dos veces.
        sale = Sale.objects.select_for_update().get(
            pk=self.pk
        )

        if sale.estado != "draft":
            raise ValidationError(
                "Solo ventas en draft pueden confirmarse"
            )

        if not sale.items.exists():
            raise ValidationError(
                "La venta no tiene items"
            )

        # Agrupa artículos con el mismo producto y envase.
        grupos = list(
            sale.items.values(
                "product_id",
                "bin_id",
            ).annotate(
                cantidad_total=Sum("cantidad"),
                bins_total=Sum("bins_cantidad"),
            ).order_by(
                "product_id",
                "bin_id",
            )
        )

        inventarios = {}

        # Bloquea y valida todos los inventarios.
        for grupo in grupos:

            clave = (
                grupo["product_id"],
                grupo["bin_id"],
            )

            try:
                inventario = (
                    Inventory.objects
                    .select_for_update()
                    .select_related("product", "bin")
                    .get(
                        usuario=sale.usuario,
                        product_id=grupo["product_id"],
                        bin_id=grupo["bin_id"],
                    )
                )

            except Inventory.DoesNotExist:
                raise ValidationError(
                    "No existe inventario para uno "
                    "de los productos seleccionados."
                )

            if inventario.cantidad < grupo["cantidad_total"]:
                raise ValidationError(
                    f"Stock insuficiente para "
                    f"{inventario.product.nombre}. "
                    f"Disponible: {inventario.cantidad}."
                )

            inventarios[clave] = inventario

        # Descuenta stock y registra movimientos.
        for grupo in grupos:

            clave = (
                grupo["product_id"],
                grupo["bin_id"],
            )

            inventario = inventarios[clave]

            inventario.cantidad -= grupo["cantidad_total"]
            inventario.save(update_fields=["cantidad"])

            InventoryMovement.objects.create(
                product_id=grupo["product_id"],
                bin_id=grupo["bin_id"],
                tipo="out",
                cantidad=grupo["cantidad_total"],
                referencia=sale.numero,
            )

            if grupo["bins_total"] > 0:

                BinMovement.objects.create(
                    cliente=sale.cliente,
                    bin_type_id=grupo["bin_id"],
                    tipo_movimiento="prestamo",
                    cantidad=grupo["bins_total"],
                    deposito_pagado=(
                        inventario.bin.valor_deposito
                        * grupo["bins_total"]
                    ),
                    usuario=sale.usuario,
                    referencia=sale.numero,
                )

        sale.estado = "confirmed"
        sale.save(update_fields=["estado"])

        # Actualiza la instancia utilizada por el serializer.
        self.estado = "confirmed"

    # =========================================
    # 🔹 PAGAR
    # =========================================

    def pay(self):

        if self.estado != "confirmed":
            raise ValidationError(
                "Solo ventas confirmadas pueden pagarse"
            )

        self.estado = "paid"
        self.save(update_fields=["estado"])

    # =========================================
    # 🔹 CANCELAR
    # =========================================

    def cancel(self):

     with transaction.atomic():

        sale = (
            Sale.objects
            .select_for_update()
            .get(pk=self.pk)
        )

        if sale.estado != "confirmed":
            raise ValidationError(
                "Solo ventas confirmadas pueden cancelarse"
            )

        grupos = list(
            sale.items.values(
                "product_id",
                "bin_id",
            ).annotate(
                cantidad_total=Sum("cantidad"),
                bins_total=Sum("bins_cantidad"),
            )
        )

        for grupo in grupos:

            try:
                inventario = (
                    Inventory.objects
                    .select_for_update()
                    .select_related("bin")
                    .get(
                        usuario=sale.usuario,
                        product_id=grupo["product_id"],
                        bin_id=grupo["bin_id"],
                    )
                )

            except Inventory.DoesNotExist:
                raise ValidationError(
                    "No existe el inventario requerido "
                    "para cancelar la venta."
                )

            inventario.cantidad += (
                grupo["cantidad_total"]
            )

            inventario.save(
                update_fields=["cantidad"]
            )

            InventoryMovement.objects.create(
                product_id=grupo["product_id"],
                bin_id=grupo["bin_id"],
                tipo="in",
                cantidad=grupo["cantidad_total"],
                referencia=f"Cancelación {sale.numero}",
            )

            if grupo["bins_total"] > 0:

                BinMovement.objects.create(
                    cliente=sale.cliente,
                    bin_type_id=grupo["bin_id"],
                    tipo_movimiento="devolucion",
                    cantidad=grupo["bins_total"],
                    deposito_pagado=(
                        inventario.bin.valor_deposito
                        * grupo["bins_total"]
                    ),
                    usuario=sale.usuario,
                    referencia=(
                        f"Cancelación {sale.numero}"
                    ),
                )

        sale.estado = "cancelled"

        sale.save(
            update_fields=["estado"]
        )

        self.estado = "cancelled"


# =========================================
# 🔹 SALE ITEM
# =========================================

class SaleItem(models.Model):

    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name="items"
    )

    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    bin = models.ForeignKey(
        "bins.BinType",
        on_delete=models.CASCADE
    )

    cantidad = models.PositiveIntegerField()

    bins_cantidad = models.PositiveIntegerField(default=0)

    precio_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    def save(self, *args, **kwargs):

        # 🔥 PASO 3 APLICADO
        if self.bins_cantidad != self.cantidad:
            raise ValidationError(
                "La cantidad de envases debe ser igual "
                "a la cantidad vendida."
            )

        self.subtotal = self.cantidad * self.precio_unitario
        super().save(*args, **kwargs)
        self.sale.calcular_totales()

    def delete(self, *args, **kwargs):
        sale = self.sale
        super().delete(*args, **kwargs)
        sale.calcular_totales()

    def __str__(self):
        return f"{self.product.nombre} x {self.cantidad}"