from django.db import models, transaction
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Max
from decimal import Decimal

from apps.productos.models import Product
from apps.inventario.models import Inventory
from apps.bins.models import BinMovement


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

        if self.estado != "draft":
            raise ValidationError("Solo ventas en draft pueden confirmarse")

        if not self.items.exists():
            raise ValidationError("La venta no tiene items")

        with transaction.atomic():

            # 🔍 VALIDAR STOCK
            for item in self.items.all():

                inventario = Inventory.objects.filter(
                    product=item.product,
                    bin=item.bin,
                    usuario=self.usuario
                ).first()

                if not inventario:
                    raise ValidationError(
                        f"No existe inventario para {item.product.nombre}"
                    )

                if inventario.cantidad < item.cantidad:
                    raise ValidationError(
                        f"Stock insuficiente para {item.product.nombre}"
                    )

            # 🔻 DESCONTAR STOCK
            for item in self.items.all():

                inventario = Inventory.objects.get(
                    product=item.product,
                    bin=item.bin,
                    usuario=self.usuario
                )

                inventario.cantidad -= item.cantidad
                inventario.save()

                InventoryMovement.objects.create(
                    product=item.product,
                    bin=item.bin,
                    tipo="out",
                    cantidad=item.cantidad,
                    referencia=self.numero
                )

            # 🔥 MOVIMIENTO DE BINS (PRÉSTAMO)
            for item in self.items.all():

                if item.bins_cantidad > 0:

                    BinMovement.objects.create(
                        cliente=self.cliente,
                        bin_type=item.bin,
                        tipo_movimiento="prestamo",
                        cantidad=item.bins_cantidad,
                        deposito_pagado=(
                            item.bin.valor_deposito * item.bins_cantidad
                        ),
                        usuario=self.usuario,
                        referencia=self.numero  # 🔥 PASO 4 APLICADO
                    )

            self.estado = "confirmed"
            self.save(update_fields=["estado"])

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

        if self.estado not in ["confirmed", "paid"]:
            raise ValidationError(
                "Solo ventas confirmadas o pagadas pueden cancelarse"
            )

        with transaction.atomic():

            for item in self.items.all():

                inventario = Inventory.objects.get(
                    product=item.product,
                    bin=item.bin,
                    usuario=self.usuario
                )

                inventario.cantidad += item.cantidad
                inventario.save()

                InventoryMovement.objects.create(
                    product=item.product,
                    bin=item.bin,
                    tipo="in",
                    cantidad=item.cantidad,
                    referencia=f"Cancelación {self.numero}"
                )

                # 🔥 DEVOLVER BINS
                if item.bins_cantidad > 0:

                    BinMovement.objects.create(
                        cliente=self.cliente,
                        bin_type=item.bin,
                        tipo_movimiento="devolucion",
                        cantidad=item.bins_cantidad,
                        deposito_pagado=(
                            item.bin.valor_deposito * item.bins_cantidad
                        ),
                        usuario=self.usuario,
                        referencia=f"Cancelación {self.numero}"  # 🔥 también aquí
                    )

            self.estado = "cancelled"
            self.save(update_fields=["estado"])


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
        if self.bins_cantidad > self.cantidad:
            raise ValidationError("Bins no puede ser mayor que cantidad")

        self.subtotal = self.cantidad * self.precio_unitario
        super().save(*args, **kwargs)
        self.sale.calcular_totales()

    def delete(self, *args, **kwargs):
        sale = self.sale
        super().delete(*args, **kwargs)
        sale.calcular_totales()

    def __str__(self):
        return f"{self.product.nombre} x {self.cantidad}"