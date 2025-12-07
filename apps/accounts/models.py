from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


# ----------------------------------------------------
# Custom User
# ----------------------------------------------------
class User(AbstractUser):
    rut = models.CharField(max_length=12, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)

    # Estado general de acceso
    suscripcion_activa = models.BooleanField(default=False)

    def __str__(self):
        return self.username


# ----------------------------------------------------
# Plan de suscripción
# ----------------------------------------------------
class SubscriptionPlan(models.Model):
    nombre = models.CharField(max_length=50)
    precio = models.PositiveIntegerField(default=20000)  # 20.000 mensual
    duracion_dias = models.PositiveIntegerField(default=30)

    def __str__(self):
        return f"{self.nombre} - ${self.precio}"


# ----------------------------------------------------
# Suscripción actual del usuario
# ----------------------------------------------------
class UserSubscription(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE)
    fecha_inicio = models.DateTimeField(default=timezone.now)
    fecha_fin = models.DateTimeField()
    activa = models.BooleanField(default=True)

    def __str__(self):
        return f"Suscripción de {self.usuario.username}"

    def esta_vigente(self):
        return self.activa and timezone.now() < self.fecha_fin


# ----------------------------------------------------
# Registro de pagos del usuario
# ----------------------------------------------------
class Payment(models.Model):
    ESTADOS = (
        ("pagado", "Pagado"),
        ("fallido", "Fallido"),
        ("pendiente", "Pendiente"),
    )

    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    monto = models.PositiveIntegerField()
    fecha_pago = models.DateTimeField(default=timezone.now)
    estado = models.CharField(max_length=20, choices=ESTADOS, default="pendiente")
    transaccion_id = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"Pago de {self.usuario.username} - {self.estado}"
