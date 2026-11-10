from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.models import User, UserSubscription, SubscriptionPlan, UsuarioAsociado
from apps.accounts.permissions.account_owner import es_titular
from apps.accounts.services.subscription_access import subscription_access

MAX_SECONDARIES = 2
CATALOG_CODES = [f"bintrack_mensual_{count}" for count in range(MAX_SECONDARIES + 1)]


def active_secondaries(owner):
    return UsuarioAsociado.objects.filter(
        titular=owner, activo=True, usuario_asociado__is_active=True,
    ).count()


def account_summary(owner):
    count = active_secondaries(owner)
    catalog = list(SubscriptionPlan.objects.filter(codigo__in=CATALOG_CODES).order_by("usuarios_secundarios"))
    plans = [{
        "codigo": plan.codigo, "nombre": plan.nombre,
        "secundarios": plan.usuarios_secundarios, "precio_final_clp": plan.precio,
    } for plan in catalog]
    selected = next((plan for plan in plans if plan["secundarios"] == count), None)
    subscription = UserSubscription.objects.filter(usuario=owner).first()
    return {
        "titular": {"id": owner.pk, "username": owner.username},
        "secundarios_activos": count, "max_secundarios": MAX_SECONDARIES,
        "puede_agregar": count < MAX_SECONDARIES,
        "requiere_revision": selected is None,
        "planes": plans, "plan_segun_usuarios": selected,
        "moneda": "CLP", "periodicidad": "mensual", "precios_finales": True,
        "adicional_alta_clp": 10000, "prorrateo": False,
        "fecha_fin": subscription.fecha_fin if subscription else None,
        "suscripcion_vigente": subscription.esta_vigente() if subscription else False,
        "suscripcion_acceso": subscription_access(subscription),
        "cobro_habilitado": False,
    }


def lock_owner(user):
    owner = User.objects.select_for_update().get(pk=user.pk)
    if not es_titular(owner):
        raise PermissionDenied("Solo el principal puede gestionar esta cuenta.")
    return owner


def check_capacity(owner):
    if active_secondaries(owner) >= MAX_SECONDARIES:
        raise ValidationError({"detail": "La cuenta admite como máximo dos secundarios activos."})


@transaction.atomic
def create_secondary(owner, data):
    owner = lock_owner(owner)
    check_capacity(owner)
    password = data.pop("password")
    secondary = User.objects.create_user(
        password=password,
        is_active=True,
        is_staff=False,
        is_superuser=False,
        debe_cambiar_contrasena=True,
        **data,
    )
    return UsuarioAsociado.objects.create(
        titular=owner, usuario_asociado=secondary, rol="usuario", activo=True,
    )


@transaction.atomic
def update_secondary(owner, relation_id, data):
    owner = lock_owner(owner)
    relation = get_object_or_404(
        UsuarioAsociado.objects.select_for_update().filter(titular=owner), pk=relation_id,
    )
    secondary = User.objects.select_for_update().get(pk=relation.usuario_asociado_id)
    if "activo" in data:
        active = data.pop("activo")
        if active and not (relation.activo and secondary.is_active):
            check_capacity(owner)
        relation.activo = active
        relation.save(update_fields=["activo"])
        secondary.is_active = active
    for field, value in data.items():
        setattr(secondary, field, value)
    secondary.save(update_fields=[*data, "is_active"])
    # Preserve identity, business records and any legacy role; never delete or reassign.
    relation.usuario_asociado = secondary
    return relation
