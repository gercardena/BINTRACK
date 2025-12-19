from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL


class Payment(models.Model):
    ESTADOS = (
        ("pending", "Pendiente"),
        ("approved", "Aprobado"),
        ("rejected", "Rechazado"),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="payments"
    )
    amount = models.PositiveIntegerField()
    provider = models.CharField(max_length=50)  # mercadopago, webpay, stripe, etc
    status = models.CharField(max_length=20, choices=ESTADOS, default="pending")
    external_id = models.CharField(max_length=150, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.provider} - {self.status}"


