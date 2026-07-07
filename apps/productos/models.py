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


class ProductPresentation(models.Model):

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="presentations",
    )

    bin_type = models.ForeignKey(
        "bins.BinType",
        on_delete=models.PROTECT,
        related_name="product_presentations",
    )

    precio = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    # ===============================
    # Campos opcionales futuros
    # ===============================

    unidad_medida = models.CharField(
        max_length=30,
        blank=True,
        null=True,
    )

    cantidad_por_envase = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
    )

    envase_contenido = models.ForeignKey(
        "bins.BinType",
        on_delete=models.PROTECT,
        related_name="contenido_en_presentaciones",
        blank=True,
        null=True,
    )

    cantidad_envase_contenido = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
    )

    activo = models.BooleanField(default=True)

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product", "bin_type"],
                name="unique_product_bin_presentation",
            )
        ]

    def __str__(self):
        return (
            f"{self.product.nombre} - "
            f"{self.bin_type.nombre} - "
            f"${self.precio}"
        )