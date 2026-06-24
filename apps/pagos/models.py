from django.db import models


class Pago(models.Model):

    METODO_CHOICES = [
        ("efectivo", "Efectivo"),
        ("transferencia", "Transferencia"),
        ("tarjeta", "Tarjeta"),
    ]

    sale = models.OneToOneField(
        "ventas.Sale",
        on_delete=models.PROTECT,
        related_name="pago",
    )

    monto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    metodo = models.CharField(
        max_length=20,
        choices=METODO_CHOICES,
    )

    referencia = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    fecha = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-fecha"]

    def __str__(self):
        return (
            f"Pago {self.id} - "
            f"Venta {self.sale.numero}"
        )