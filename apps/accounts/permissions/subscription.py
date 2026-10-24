from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission, SAFE_METHODS
from apps.accounts.services.subscription_access import access_for_user


class HasActiveSubscription(BasePermission):
    """Business data stays readable; writes require a current or grace period.

    Kept under the existing class name for compatibility. Account management,
    authentication and subscription payments are deliberately separate.
    """

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        access = access_for_user(user)
        if request.method in SAFE_METHODS or access["puede_operar"]:
            return True
        raise PermissionDenied({
            "code": "subscription_read_only",
            "detail": "La cuenta está en modo solo lectura. Puedes consultar tus datos, "
                      "pero no registrar ni modificar operaciones. El principal debe regularizar la suscripción.",
            "estado": access["estado"],
        })
