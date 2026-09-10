from apps.accounts.models import UsuarioAsociado


def get_usuario_titular(user):
    """
    Devuelve el usuario titular operativo.

    Si el usuario autenticado es un usuario asociado activo,
    devuelve el titular de la suscripción.

    Si no tiene relación activa, devuelve el mismo usuario.
    """

    relacion = UsuarioAsociado.objects.filter(
        usuario_asociado=user,
        activo=True,
    ).select_related(
        "titular",
    ).first()

    if relacion:
        return relacion.titular

    return user