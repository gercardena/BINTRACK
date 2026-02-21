from django.db import models
from django.conf import settings
from apps.productos.models import Product


class Inventory(models.Model):

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="inventories"
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="inventories"
    )

    bin = models.ForeignKey(
        "bins.BinType",
        on_delete=models.CASCADE,
        related_name="inventories"
    )

    cantidad = models.PositiveIntegerField(default=0)

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("product", "bin")
        verbose_name = "Inventory"
        verbose_name_plural = "Inventories"

    def __str__(self):
        return f"{self.product.nombre} - {self.bin.nombre} ({self.cantidad})"
