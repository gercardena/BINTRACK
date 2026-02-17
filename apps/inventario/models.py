from django.db import models


class Inventory(models.Model):

    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)

    cantidad = models.IntegerField(default=0)

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nombre

