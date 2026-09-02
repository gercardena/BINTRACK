from django.db import models
from django.conf import settings


class Product(models.Model):

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )

    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True, null=True)

    # Precio base referencial del producto.
    # Las ventas usan principalmente el precio de la presentación.
    precio = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    activo = models.BooleanField(default=True)

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nombre


class ProductPresentation(models.Model):

    TIPO_COBRO_CHOICES = [
        ("envase", "Por envase"),
        ("kilo", "Por kilo"),
    ]

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

    # Si tipo_cobro = envase, este precio es por envase completo.
    # Si tipo_cobro = kilo, este precio es por kilo pesado.
    precio = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    tipo_cobro = models.CharField(
        max_length=20,
        choices=TIPO_COBRO_CHOICES,
        default="envase",
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
            f"{self.get_tipo_cobro_display()} - "
            f"${self.precio}"
        )