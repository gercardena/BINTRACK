from datetime import timedelta
from uuid import uuid4

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.accounts.models import SubscriptionPlan, UserSubscription, UsuarioAsociado
from apps.accounts.services.account_management import lock_owner, MAX_SECONDARIES
from apps.payments.models import Payment
from .configuration import PaymentConflict, PaymentsUnavailable, preference_urls, test_config
from .mercadopago import MercadoPagoService


def current_quote(owner):
    ids = list(UsuarioAsociado.objects.filter(
        titular=owner, activo=True, usuario_asociado__is_active=True,
    ).order_by("usuario_asociado_id").values_list("usuario_asociado_id", flat=True))
    if len(ids) > MAX_SECONDARIES:
        raise ValidationError("Revisa la cantidad de usuarios antes de pagar.")
    plan = SubscriptionPlan.objects.filter(codigo=f"bintrack_mensual_{len(ids)}").first()
    if plan is None or plan.precio != 50000 + 10000 * len(ids):
        raise PaymentsUnavailable("El catálogo mensual requiere revisión.")
    subscription = UserSubscription.objects.filter(usuario=owner).first()
    return plan, ids, subscription.fecha_fin if subscription else None


def create_checkout(owner):
    test_config()
    preference_urls()
    # Persist correlation BEFORE contacting MP. An uncertain timeout must never
    # erase the local order or automatically create another preference.
    with transaction.atomic():
        owner = lock_owner(owner)
        if Payment.objects.filter(user=owner, environment="sandbox", needs_review=True).exists():
            raise PaymentConflict()
        plan, ids, due = current_quote(owner)
        pending = Payment.objects.filter(
            user=owner, environment="sandbox", applied_at__isnull=True,
            expires_at__gt=timezone.now(),
        ).order_by("-id").first()
        if pending:
            if (pending.secondary_ids != ids or pending.expected_due_at != due
                    or pending.plan_code != plan.codigo or pending.amount != plan.precio):
                raise PaymentConflict("La cuenta cambió desde el enlace pendiente. Revisa ese pago antes de continuar.")
            if not pending.checkout_url:
                raise PaymentConflict("El enlace anterior está en preparación o pendiente de verificación.")
            return pending, False
        payment = Payment.objects.create(
            user=owner, amount=plan.precio, provider="mercadopago", reference=uuid4(),
            environment="sandbox", plan_code=plan.codigo, secondary_ids=ids,
            expected_due_at=due, expires_at=timezone.now() + timedelta(hours=24),
        )
    try:
        preference = MercadoPagoService().crear_preferencia(payment)
    except PaymentsUnavailable:
        Payment.objects.filter(pk=payment.pk, applied_at__isnull=True).update(
            needs_review=True, review_reason="checkout_creation_uncertain",
        )
        raise
    Payment.objects.filter(pk=payment.pk).update(
        external_id=preference["id"], checkout_url=preference["init_point"],
    )
    payment.refresh_from_db()
    return payment, True
