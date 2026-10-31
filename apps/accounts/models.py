from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


# ----------------------------------------------------
# Custom User
# ----------------------------------------------------
class User(AbstractUser):
    rut = models.CharField(
        max_length=12,
        blank=True,
        null=True,
    )

    telefono = models.CharField(
        max_length=20,
        blank=True,
        null=True,
    )

    # Estado general de acceso
    suscripcion_activa = models.BooleanField(
        default=False,
    )

    def __str__(self):
        return self.username


# ----------------------------------------------------
# Plan de suscripción
# ----------------------------------------------------
class SubscriptionPlan(models.Model):
    # Stable identifiers for the monthly catalog. Null keeps historical plans intact.
    codigo = models.CharField(max_length=40, unique=True, null=True, blank=True)
    usuarios_secundarios = models.PositiveSmallIntegerField(null=True, blank=True)

    nombre = models.CharField(
        max_length=50,
    )

    precio = models.PositiveIntegerField(
        default=20000,
    )

    duracion_dias = models.PositiveIntegerField(
        default=30,
    )

    def __str__(self):
        return f"{self.nombre} - ${self.precio}"


# ----------------------------------------------------
# Suscripción actual del usuario titular
# ----------------------------------------------------
class UserSubscription(models.Model):
    usuario = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
    )

    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.CASCADE,
    )

    fecha_inicio = models.DateTimeField(
        default=timezone.now,
    )

    fecha_fin = models.DateTimeField()

    # Retain the original monthly billing day across short months (31 -> 28 -> 31).
    dia_facturacion = models.PositiveSmallIntegerField(null=True, blank=True)

    activa = models.BooleanField(
        default=True,
    )

    def __str__(self):
        return f"Suscripción de {self.usuario.username}"

    def esta_vigente(self):
        return self.activa and self.fecha_inicio <= timezone.now() < self.fecha_fin


# ----------------------------------------------------
# Periodos administrativos de marcha blanca
# ----------------------------------------------------
class SubscriptionGrant(models.Model):
    """Auditable administrative grant; it is never created by the mobile app."""

    owner = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="subscription_grants",
    )
    granted_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="subscription_grants_made",
    )
    reason = models.CharField(max_length=250)
    previous_end = models.DateTimeField(null=True, blank=True)
    granted_from = models.DateTimeField()
    granted_until = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Marcha blanca: {self.owner.username} hasta {self.granted_until:%Y-%m-%d}"


# ----------------------------------------------------
# Usuario asociado a una suscripción/titular
# ----------------------------------------------------
class UsuarioAsociado(models.Model):
    ROL_CHOICES = [
        ("usuario", "Usuario asociado"),
        ("admin", "Administrador"),
    ]

    titular = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="usuarios_asociados",
    )

    usuario_asociado = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="relacion_titular",
    )

    rol = models.CharField(
        max_length=20,
        choices=ROL_CHOICES,
        default="usuario",
    )

    activo = models.BooleanField(
        default=True,
    )

    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["titular", "usuario_asociado"],
                name="unique_titular_usuario_asociado",
            ),
        ]

    def __str__(self):
        return (
            f"{self.usuario_asociado.username} "
            f"asociado a {self.titular.username}"
        )
