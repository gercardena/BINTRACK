from django.db import models
from django.utils import timezone
from django.conf import settings


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
    observaciones = models.TextField(blank=True, default="", max_length=2000)
    version = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-fecha_emision"]

    def __str__(self):
        return f"Factura {self.numero}"


class FacturaCambio(models.Model):
    factura = models.ForeignKey(Factura, on_delete=models.PROTECT, related_name="cambios")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    usuario_nombre = models.CharField(max_length=150)
    fecha = models.DateTimeField(default=timezone.now)
    cambios = models.JSONField()

    class Meta:
        ordering = ["-fecha", "-id"]
