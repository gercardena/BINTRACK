from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework_simplejwt.tokens import RefreshToken
from .permissions.account_owner import es_titular
from .services.users import get_usuario_titular
from .services.subscription_access import subscription_access

from .models import (
    User,
    SubscriptionPlan,
    UserSubscription,
)


# ----------------------------------------------------
# Serializer: REGISTRO DE USUARIO
# ----------------------------------------------------
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password",
            "rut",
            "telefono",
        ]

    def create(self, validated_data):
        password = validated_data.pop("password")

        user = User(**validated_data)
        user.set_password(password)
        user.suscripcion_activa = False
        user.save()

        return user


# ----------------------------------------------------
# Serializer: LOGIN (JWT)
# ----------------------------------------------------
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get("email")
        password = data.get("password")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({
                "email": "El email no está registrado."
            })

        user = authenticate(
            username=user.username,
            password=password,
        )

        if not user:
            raise serializers.ValidationError({
                "password": "Contraseña incorrecta."
            })

        if not user.is_active:
            raise serializers.ValidationError(
                "La cuenta está desactivada."
            )

        get_usuario_titular(user)  # Reject a disabled secondary before issuing tokens.
        refresh = RefreshToken.for_user(user)

        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
            },
        }


# ----------------------------------------------------
# Serializer: ESTADO DE SUSCRIPCIÓN
# ----------------------------------------------------
class UserSubscriptionSerializer(serializers.ModelSerializer):
    plan = serializers.CharField(source="plan.nombre")
    precio = serializers.IntegerField(source="plan.precio")
    duracion = serializers.IntegerField(source="plan.duracion_dias")

    class Meta:
        model = UserSubscription
        fields = [
            "plan",
            "precio",
            "duracion",
            "fecha_inicio",
            "fecha_fin",
            "activa",
        ]


# ----------------------------------------------------
# Serializer: PERFIL USUARIO (ENDPOINT PROTEGIDO)
# ----------------------------------------------------
class UserProfileSerializer(serializers.ModelSerializer):
    suscripcion_acceso = serializers.SerializerMethodField()
    puede_gestionar_cuenta = serializers.SerializerMethodField()
    suscripcion_activa = serializers.SerializerMethodField()
    suscripcion_plan = serializers.SerializerMethodField()
    suscripcion_fecha_fin = serializers.SerializerMethodField()
    suscripcion_estado = serializers.SerializerMethodField()
    titular_id = serializers.SerializerMethodField()
    titular_username = serializers.SerializerMethodField()
    es_usuario_asociado = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "rut",
            "telefono",
            "suscripcion_activa",
            "suscripcion_plan",
            "suscripcion_fecha_fin",
            "suscripcion_estado",
            "titular_id",
            "titular_username",
            "es_usuario_asociado",
            "debe_cambiar_contrasena",
            "puede_gestionar_cuenta",
            "suscripcion_acceso",
        ]

    def get_titular(self, user):
        titular = self.context.get("titular")

        if titular:
            return titular

        return user

    def get_puede_gestionar_cuenta(self, user):
        return es_titular(user)

    def get_suscripcion(self, user):
        titular = self.get_titular(user)

        return UserSubscription.objects.filter(
            usuario=titular,
        ).select_related(
            "plan",
        ).first()

    def get_suscripcion_activa(self, user):
        subscription = self.get_suscripcion(user)

        if not subscription:
            return False

        return subscription_access(subscription)["estado"] == "activa"

    def get_suscripcion_plan(self, user):
        subscription = self.get_suscripcion(user)

        if not subscription:
            return None

        return subscription.plan.nombre

    def get_suscripcion_fecha_fin(self, user):
        subscription = self.get_suscripcion(user)

        if not subscription:
            return None

        return subscription.fecha_fin

    def get_suscripcion_estado(self, user):
        return self.get_suscripcion_acceso(user)["estado"]

    def get_suscripcion_acceso(self, user):
        return subscription_access(self.get_suscripcion(user))

    def get_titular_id(self, user):
        titular = self.get_titular(user)

        return titular.id

    def get_titular_username(self, user):
        titular = self.get_titular(user)

        return titular.username

    def get_es_usuario_asociado(self, user):
        titular = self.get_titular(user)

        return titular.id != user.id


class ChangePasswordSerializer(serializers.Serializer):
    contrasena_actual = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        max_length=128,
    )
    nueva_contrasena = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        max_length=128,
    )

    def validate(self, attrs):
        user = self.context["request"].user
        current = attrs["contrasena_actual"]
        new = attrs["nueva_contrasena"]

        if not user.check_password(current):
            raise serializers.ValidationError({
                "contrasena_actual": "La contraseña actual no es correcta.",
            })
        if new != new.strip():
            raise serializers.ValidationError({
                "nueva_contrasena": "No uses espacios al inicio o al final.",
            })
        if current == new:
            raise serializers.ValidationError({
                "nueva_contrasena": "Elige una contraseña distinta a la temporal.",
            })
        try:
            validate_password(new, user)
        except DjangoValidationError as error:
            raise serializers.ValidationError({
                "nueva_contrasena": list(error.messages),
            }) from error

        return attrs
