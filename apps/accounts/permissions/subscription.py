from rest_framework.permissions import BasePermission

from apps.accounts.models import UserSubscription
from apps.accounts.services.users import get_usuario_titular


class HasActiveSubscription(BasePermission):
    """
    Permite acceso solo a usuarios con suscripción activa.

    Si el usuario es asociado, se valida la suscripción
    del usuario titular.
    """

    message = "Tu suscripción no está activa."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        titular = get_usuario_titular(user)

        subscription = (
            UserSubscription.objects
            .filter(
                usuario=titular,
                activa=True,
            )
            .first()
        )

        if subscription is None:
            return False

        return subscription.esta_vigente()
