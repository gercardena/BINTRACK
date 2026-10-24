"""Subscription access is computed on every request, never from the legacy flag."""
from datetime import timedelta, timezone as dt_timezone

from django.utils import timezone

from apps.accounts.models import UserSubscription
from .users import get_usuario_titular

GRACE_DAYS = 3


def subscription_access(subscription, *, at=None):
    now = at if at is not None else timezone.now()
    end = subscription.fecha_fin if subscription else None
    # Exactly 72 hours, including a daylight-saving transition.
    grace_end = end.astimezone(dt_timezone.utc) + timedelta(days=GRACE_DAYS) if end else None
    if subscription is None:
        state = "sin_suscripcion"
    elif not subscription.activa:
        state = "inactiva"
    elif now < subscription.fecha_inicio:
        state = "pendiente"
    elif now < end:
        state = "activa"
    elif now < grace_end:
        state = "en_gracia"
    else:
        state = "vencida"
    writable = state in ("activa", "en_gracia")
    return {
        "estado": state,
        "puede_operar": writable,
        "solo_lectura": not writable,
        "fecha_fin": end.isoformat() if end else None,
        "gracia_hasta": grace_end.isoformat() if grace_end else None,
        "dias_gracia": GRACE_DAYS,
    }


def access_for_user(user, *, at=None):
    owner = get_usuario_titular(user)
    subscription = UserSubscription.objects.filter(usuario=owner).first()
    return subscription_access(subscription, at=at)
