"""Only verified provider data may enter this single transactional settlement path."""
from decimal import Decimal, InvalidOperation
from uuid import UUID
import re

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import NotFound, ValidationError

from apps.accounts.models import User
from apps.accounts.permissions.account_owner import es_titular
from apps.accounts.services.monthly_periods import renew_monthly_period
from apps.payments.models import Payment, PaymentAttempt
from .checkout import current_quote
from .configuration import PaymentsUnavailable, test_config
from .mercadopago import MercadoPagoService

PROVIDER_STATUSES = {"pending", "in_process", "authorized", "approved", "rejected",
                     "cancelled", "refunded", "charged_back", "in_mediation"}
REVERSED = {"refunded", "charged_back"}


def provider_date(value):
    try:
        parsed = parse_datetime(value) if isinstance(value, str) else None
    except ValueError:
        parsed = None
    if parsed is None or timezone.is_naive(parsed):
        raise ValidationError("La respuesta del proveedor no contiene una fecha válida.")
    return parsed


def amount(value):
    try:
        result = Decimal(str(value))
        if not result.is_finite() or result < 0:
            raise InvalidOperation
        return result
    except (InvalidOperation, ValueError):
        raise ValidationError("El proveedor devolvió un importe inválido.") from None


def flag_review(payment, reason):
    payment.needs_review = True
    payment.review_reason = reason


def verify_test_environment(data, order, config):
    if data.get("live_mode") is False:
        return
    buyer = str(getattr(settings, "MERCADOPAGO_TEST_BUYER_ID", ""))
    owner = str(getattr(settings, "MERCADOPAGO_TEST_LOCAL_OWNER_ID", ""))
    payer = data.get("payer")
    if (data.get("live_mode") is not True
            or getattr(settings, "MERCADOPAGO_TEST_ALLOW_TEST_USERS_LIVE_MODE", False) is not True
            or not re.fullmatch(r"[0-9]{1,30}", buyer)
            or not re.fullmatch(r"[0-9]{1,30}", owner)
            or buyer == config.collector_id or str(order.user_id) != owner
            or not isinstance(payer, dict) or str(payer.get("id")) != buyer):
        raise ValidationError("El entorno de prueba no está autorizado para esta cuenta.")
    # Never trust the notification's live_mode or a token prefix. This exception
    # requires fresh authenticated proof that the credential belongs to a TEST
    # seller, plus explicitly pinned test buyer and local principal. No caching.
    MercadoPagoService().verificar_vendedor_prueba()


def reconcile(provider_id, data, *, expected_order=None):
    config = test_config()
    if not isinstance(data, dict) or str(data.get("id")) != str(provider_id):
        raise ValidationError("El pago consultado no coincide con la notificación.")
    try:
        reference = UUID(str(data.get("external_reference")))
    except (ValueError, TypeError, AttributeError):
        raise ValidationError("El pago no corresponde a una orden nueva de BinTrack.") from None
    lookup = Payment.objects.filter(reference=reference, environment="sandbox", provider="mercadopago")
    if expected_order is not None:
        lookup = lookup.filter(pk=expected_order.pk, user_id=expected_order.user_id)
    order = lookup.first()
    if order is None:
        raise NotFound("El pago no corresponde a esta orden.")
    status = data.get("status")
    if (not isinstance(status, str) or status not in PROVIDER_STATUSES
            or str(data.get("collector_id")) != config.collector_id
            or data.get("currency_id") != "CLP" or amount(data.get("transaction_amount")) != order.amount):
        raise ValidationError("El entorno, vendedor, estado, moneda o importe no coincide con la orden.")
    verify_test_environment(data, order, config)
    updated = provider_date(data.get("date_last_updated"))
    refunded = amount(data.get("transaction_amount_refunded", 0))
    approved_at = provider_date(data.get("date_approved")) if status == "approved" else None

    with transaction.atomic():
        # Same lock order as account management and renew_monthly_period.
        owner = User.objects.select_for_update().get(pk=order.user_id)
        payment = Payment.objects.select_for_update().get(pk=order.pk)
        attempt, created = PaymentAttempt.objects.get_or_create(
            provider_payment_id=str(provider_id),
            defaults={"payment": payment, "status": status, "provider_updated_at": updated},
        )
        if attempt.payment_id != payment.pk:
            raise ValidationError("El identificador del proveedor ya pertenece a otra orden.")
        if not created:
            if (attempt.provider_updated_at > updated
                    or (attempt.status in REVERSED and status not in REVERSED)
                    or (attempt.status == "approved" and status not in {"approved", *REVERSED, "in_mediation"})):
                return payment
            attempt.status = status
            attempt.provider_updated_at = updated
            attempt.save(update_fields=["status", "provider_updated_at", "observed_at"])

        if status in REVERSED or status == "in_mediation" or refunded > 0:
            flag_review(payment, "refund_or_dispute")
            if status in REVERSED and (not payment.applied_provider_id or payment.applied_provider_id == str(provider_id)):
                payment.status = status
            # No automatic deletion of business data or retroactive date changes.
        elif status == "approved":
            if payment.applied_at:
                if payment.applied_provider_id != str(provider_id):
                    flag_review(payment, "multiple_approved_payments")
            elif payment.needs_review and payment.review_reason != "checkout_creation_uncertain":
                pass  # A known anomaly requires human review, not another retry.
            else:
                payment.status = "approved"
                if (payment.expires_at is None or approved_at > payment.expires_at
                        or approved_at < payment.created_at or approved_at > updated):
                    flag_review(payment, "approval_outside_quote")
                elif not es_titular(owner):
                    flag_review(payment, "owner_not_eligible")
                else:
                    try:
                        plan, ids, due = current_quote(owner)
                    except (ValidationError, PaymentsUnavailable):
                        flag_review(payment, "account_changed")
                    else:
                        if (ids != payment.secondary_ids or plan.codigo != payment.plan_code
                                or plan.precio != payment.amount or due != payment.expected_due_at):
                            flag_review(payment, "account_or_period_changed")
                        else:
                            subscription = renew_monthly_period(owner, at=approved_at)
                            payment.applied_at = timezone.now()
                            payment.applied_until = subscription.fecha_fin
                            payment.applied_provider_id = str(provider_id)
                            payment.needs_review = False
                            payment.review_reason = ""
        elif not payment.applied_at and not payment.needs_review:
            payment.status = status if status in {"rejected", "cancelled"} else "pending"
        payment.save(update_fields=["status", "needs_review", "review_reason", "applied_at",
                                    "applied_until", "applied_provider_id"])
        return payment
