from django.db import models, transaction
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Max
from decimal import Decimal

from apps.productos.models import Product
from apps.inventario.models import Inventory


IVA_RATE = Decimal("0.19")


# =========================================
# 🔹 INVENTORY MOVEMENT (PRIMERO)
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

    numero = models.CharField(max_length=20, unique=True, blank=True)

    estado = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    iva = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha_creacion"]

    def generar_numero(self):
        ultimo = Sale.objects.aggregate(Max("id"))["id__max"]
        siguiente = (ultimo or 0) + 1
        return f"V{siguiente:04d}"

    def calcular_totales(self):
        items = self.items.all()
        subtotal = sum((item.subtotal for item in items), Decimal("0.00"))
        iva = subtotal * IVA_RATE
        total = subtotal + iva

        self.subtotal = subtotal
        self.iva = iva
        self.total = total

        super().save(update_fields=["subtotal", "iva", "total"])

    def save(self, *args, **kwargs):

        with transaction.atomic():

            es_nueva = self.pk is None

            if es_nueva and not self.numero:
                self.numero = self.generar_numero()

            if self.pk:
                venta_original = Sale.objects.get(pk=self.pk)
            else:
                venta_original = None

            super().save(*args, **kwargs)

            if (
                self.estado == "confirmed"
                and (not venta_original or venta_original.estado != "confirmed")
            ):

                for item in self.items.all():

                    inventario = Inventory.objects.filter(
                        product=item.product,
                        bin=item.bin
                    ).first()

                    if not inventario:
                        raise ValidationError(
                            f"No existe inventario para {item.product.nombre}"
                        )

                    if inventario.cantidad < item.cantidad:
                        raise ValidationError(
                            f"Stock insuficiente para {item.product.nombre}"
                        )

                for item in self.items.all():

                    inventario = Inventory.objects.get(
                        product=item.product,
                        bin=item.bin
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

            if (
                self.estado == "cancelled"
                and venta_original
                and venta_original.estado in ["confirmed", "paid"]
            ):

                for item in self.items.all():

                    inventario = Inventory.objects.get(
                        product=item.product,
                        bin=item.bin
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

    def __str__(self):
        return f"Venta {self.numero}"


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
    bin = models.ForeignKey("bins.BinType", on_delete=models.CASCADE)

    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    def save(self, *args, **kwargs):
        self.subtotal = self.cantidad * self.precio_unitario
        super().save(*args, **kwargs)
        self.sale.calcular_totales()

    def delete(self, *args, **kwargs):
        sale = self.sale
        super().delete(*args, **kwargs)
        sale.calcular_totales()

    def __str__(self):
        return f"{self.product.nombre} x {self.cantidad}"