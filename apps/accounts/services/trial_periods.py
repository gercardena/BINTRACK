"""Controlled administrative grants for the closed march-white program."""

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.models import SubscriptionGrant, SubscriptionPlan, User, UserSubscription

from .account_management import MAX_SECONDARIES, active_secondaries
from .monthly_periods import next_month
from .users import get_usuario_titular


@transaction.atomic
def grant_march_white_period(owner, *, granted_by: User, reason: str, at=None):
    """Grant exactly one calendar month, keeping a persistent audit record.

    This is intentionally an internal operation: it is not evidence of a
    Mercado Pago payment and is never exposed through the mobile API.
    """
    reason = reason.strip()
    if not reason:
        raise ValidationError("Indica el motivo de la activación de marcha blanca.")
    if len(reason) > 250:
        raise ValidationError("El motivo puede tener hasta 250 caracteres.")
    if not granted_by.is_active or not granted_by.is_staff:
        raise PermissionDenied("Solo un administrador activo puede otorgar marcha blanca.")
    if get_usuario_titular(owner).pk != owner.pk:
        raise PermissionDenied("La marcha blanca solo se puede otorgar al usuario titular.")

    owner = User.objects.select_for_update().get(pk=owner.pk)
    now = at if at is not None else timezone.now()
    secondary_count = active_secondaries(owner)
    if secondary_count > MAX_SECONDARIES:
        raise ValidationError("Revisa la cantidad de secundarios antes de otorgar el período.")

    plan = SubscriptionPlan.objects.get(codigo=f"bintrack_mensual_{secondary_count}")
    subscription = UserSubscription.objects.select_for_update().filter(usuario=owner).first()
    previous_end = subscription.fecha_fin if subscription else None

    # A current account keeps its already-paid time. An expired one begins now.
    starts_from = previous_end if previous_end and previous_end > now else now
    billing_day = (
        subscription.dia_facturacion
        if subscription and subscription.dia_facturacion and previous_end and previous_end > now
        else timezone.localtime(starts_from, timezone.get_default_timezone()).day
    )
    ends_at = next_month(starts_from, billing_day)

    if subscription is None:
        subscription = UserSubscription(usuario=owner, fecha_inicio=now)
    elif previous_end is None or previous_end <= now:
        subscription.fecha_inicio = now

    subscription.plan = plan
    subscription.fecha_fin = ends_at
    subscription.dia_facturacion = billing_day
    subscription.activa = True
    subscription.save()

    return SubscriptionGrant.objects.create(
        owner=owner,
        granted_by=granted_by,
        reason=reason,
        previous_end=previous_end,
        granted_from=starts_from,
        granted_until=ends_at,
    )
