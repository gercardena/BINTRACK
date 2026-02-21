from django.db import models
from django.conf import settings


class Product(models.Model):

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True, null=True)

    # pensado para frutas (venta futura)
    precio = models.DecimalField(max_digits=10, decimal_places=2)

    activo = models.BooleanField(default=True)

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nombre
