from datetime import timedelta
from django.utils import timezone

from apps.accounts.models import User, SubscriptionPlan, UserSubscription


def activate_subscription_for_user(user: User):
    """
    Activa o renueva la suscripción del usuario
    """

    # 1️⃣ Obtener plan (por ahora el primero)
    plan = SubscriptionPlan.objects.first()

    if not plan:
        raise Exception("No hay planes de suscripción creados")

    now = timezone.now()

    # 2️⃣ Buscar suscripción existente
    subscription = UserSubscription.objects.filter(usuario=user).first()

    if subscription and subscription.fecha_fin > now:
        # 🔁 Renovar
        subscription.fecha_fin += timedelta(days=plan.duracion_dias)
    else:
        # 🆕 Crear nueva
        subscription = UserSubscription.objects.create(
            usuario=user,
            plan=plan,
            fecha_inicio=now,
            fecha_fin=now + timedelta(days=plan.duracion_dias),
            activa=True
        )

    subscription.save()

    # 3️⃣ Activar flag en usuario
    user.suscripcion_activa = True
    user.save()

    return subscription