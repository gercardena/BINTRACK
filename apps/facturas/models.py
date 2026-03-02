from django.db import models
from django.utils import timezone


class Factura(models.Model):

    sale = models.OneToOneField(
        "ventas.Sale",
        on_delete=models.PROTECT,
        related_name="factura"
    )

    numero = models.CharField(max_length=20, unique=True)

    # Snapshot del cliente (NO dinámico)
    cliente_nombre = models.CharField(max_length=255)
    cliente_rut = models.CharField(max_length=20)
    cliente_direccion = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    iva = models.DecimalField(max_digits=12, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2)

    fecha_emision = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-fecha_emision"]

    def __str__(self):
        return f"Factura {self.numero}"
