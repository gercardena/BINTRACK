from rest_framework.permissions import BasePermission


class HasActiveSubscription(BasePermission):
    """
    Permite acceso solo a usuarios con suscripción activa
    """
    message = "Tu suscripción no está activa."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        return user.suscripcion_activa is True
