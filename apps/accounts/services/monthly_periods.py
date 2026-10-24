"""Calendar-month renewal primitive. Not a payment endpoint or payment proof.

Stage 3 must call this only after verified, idempotent payment reconciliation.
The historical Mercado Pago callbacks are NOT connected to this function yet.
"""
from calendar import monthrange
from datetime import timezone as dt_timezone

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.accounts.models import SubscriptionPlan, UserSubscription
from .account_management import active_secondaries, lock_owner, MAX_SECONDARIES


def next_month(start, billing_day):
    if not 1 <= billing_day <= 31:
        raise ValueError("Billing day must be between 1 and 31")
    local = timezone.localtime(start, timezone.get_default_timezone())
    year = local.year + (local.month == 12)
    month = local.month % 12 + 1
    end = local.replace(year=year, month=month, day=min(billing_day, monthrange(year, month)[1]))
    # Normalize a nonexistent local hour at the Chilean DST spring transition.
    return end.astimezone(dt_timezone.utc).astimezone(local.tzinfo)


@transaction.atomic
def renew_monthly_period(owner, *, at=None):
    owner = lock_owner(owner)
    now = at if at is not None else timezone.now()
    count = active_secondaries(owner)
    if count > MAX_SECONDARIES:
        raise ValidationError("Revisa la cantidad de secundarios antes de renovar.")
    plan = SubscriptionPlan.objects.get(codigo=f"bintrack_mensual_{count}")
    subscription = UserSubscription.objects.select_for_update().filter(usuario=owner).first()
    # Every renewal adds one month to the recorded due date, even after grace.
    # No unpaid months are silently waived or charged here.
    start = subscription.fecha_fin if subscription else now
    day = (subscription.dia_facturacion if subscription else None) or timezone.localtime(
        start, timezone.get_default_timezone(),
    ).day
    end = next_month(start, day)
    if subscription is None:
        subscription = UserSubscription(usuario=owner)
    if subscription.pk is None:
        subscription.fecha_inicio = now
    subscription.plan = plan
    subscription.fecha_fin = end
    subscription.dia_facturacion = day
    subscription.activa = True
    subscription.save()
    return subscription
