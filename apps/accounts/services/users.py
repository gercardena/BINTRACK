from apps.accounts.models import UsuarioAsociado
from rest_framework.exceptions import PermissionDenied


def get_usuario_titular(user):
    """
    Devuelve el usuario titular operativo.

    Un asociado desactivado nunca se convierte en titular independiente.
    """

    relacion = UsuarioAsociado.objects.filter(
        usuario_asociado=user,
    ).select_related(
        "titular",
    ).first()

    if relacion:
        if not relacion.activo or not user.is_active or not relacion.titular.is_active:
            raise PermissionDenied("Tu acceso a esta cuenta está desactivado. Contacta al principal.")
        return relacion.titular

    return user
