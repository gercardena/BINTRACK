from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL


class Payment(models.Model):
    ESTADOS = (
        ("pending", "Pendiente"),
        ("approved", "Aprobado"),
        ("rejected", "Rechazado"),
        ("cancelled", "Cancelado"),
        ("refunded", "Reembolsado"),
        ("charged_back", "Contracargo"),
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

    # Historical rows remain without a reference: they must not grant new periods.
    reference = models.UUIDField(null=True, blank=True, unique=True, editable=False)
    environment = models.CharField(max_length=20, blank=True)
    plan_code = models.CharField(max_length=40, blank=True)
    secondary_ids = models.JSONField(default=list, blank=True)
    expected_due_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    checkout_url = models.URLField(max_length=1000, blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    applied_until = models.DateTimeField(null=True, blank=True)
    applied_provider_id = models.CharField(max_length=100, blank=True)
    needs_review = models.BooleanField(default=False)
    review_reason = models.CharField(max_length=60, blank=True)

    def __str__(self):
        return f"{self.user} - {self.provider} - {self.status}"


class PaymentAttempt(models.Model):
    """A provider payment belongs to one order, regardless of notification count."""
    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name="attempts")
    provider_payment_id = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=30)
    provider_updated_at = models.DateTimeField()
    observed_at = models.DateTimeField(auto_now=True)


