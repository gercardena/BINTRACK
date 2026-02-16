from django.db import models
from django.conf import settings


# -------------------------------
# Tipo de envase
# -------------------------------
class BinType(models.Model):

    nombre = models.CharField(max_length=100)
    material = models.CharField(max_length=50)
    valor_deposito = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.nombre


# -------------------------------
# Cliente (por usuario/bodega)
# -------------------------------
class Cliente(models.Model):

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    nombre = models.CharField(max_length=150)
    telefono = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.nombre} ({self.usuario})"


# -------------------------------
# Movimiento de bins
# -------------------------------
class BinMovement(models.Model):

    MOVIMIENTO_CHOICES = [
        ("entrada", "Entrada inventario"),
        ("prestamo", "Prestamo cliente"),
        ("devolucion", "Devolucion cliente"),
        ("baja", "Baja inventario"),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    bin_type = models.ForeignKey(
        BinType,
        on_delete=models.CASCADE
    )

    tipo_movimiento = models.CharField(
        max_length=20,
        choices=MOVIMIENTO_CHOICES
    )

    cantidad = models.IntegerField()

    deposito_pagado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tipo_movimiento} - {self.bin_type} ({self.cantidad})"