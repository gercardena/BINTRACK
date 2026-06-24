from django.conf import settings
from django.db import models


class Client(models.Model):

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="clients",
    )

    nombre = models.CharField(
        max_length=255,
    )

    rut = models.CharField(
        max_length=20,
        unique=True,
    )

    email = models.EmailField(
        blank=True,
        null=True,
    )

    telefono = models.CharField(
        max_length=20,
        blank=True,
        null=True,
    )

    direccion = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    activo = models.BooleanField(
        default=True,
    )

    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.rut})"