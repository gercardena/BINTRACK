from rest_framework.permissions import BasePermission

from apps.accounts.models import UsuarioAsociado


def es_titular(user):
    # An inactive relation or the legacy role "admin" never grants ownership.
    return bool(
        user and user.is_authenticated and user.is_active
        and not UsuarioAsociado.objects.filter(usuario_asociado=user).exists()
    )


class IsAccountOwner(BasePermission):
    message = "Solo el usuario principal puede gestionar usuarios y suscripción."

    def has_permission(self, request, view):
        return es_titular(request.user)
