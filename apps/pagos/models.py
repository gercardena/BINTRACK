from django.db import models
from apps.facturas.models import Factura

class Pago(models.Model):

    METODO_CHOICES = [
        ("efectivo", "Efectivo"),
        ("transferencia", "Transferencia"),
        ("tarjeta", "Tarjeta"),
    ]

    factura = models.ForeignKey(
        Factura,
        on_delete=models.CASCADE,
        related_name="pagos"
    )

    monto = models.DecimalField(max_digits=10, decimal_places=2)

    metodo = models.CharField(
        max_length=20,
        choices=METODO_CHOICES
    )

    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pago {self.id} - Factura {self.factura.id}"