from rest_framework import serializers
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, SubscriptionPlan, UserSubscription


# ----------------------------------------------------
# Serializer: REGISTRO DE USUARIO
# ----------------------------------------------------
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'rut', 'telefono']

    def create(self, validated_data):
        password = validated_data.pop('password')

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

        # Buscar usuario por email
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({"email": "El email no está registrado."})

        # Autenticar
        user = authenticate(username=user.username, password=password)

        if not user:
            raise serializers.ValidationError({"password": "Contraseña incorrecta."})

        if not user.is_active:
            raise serializers.ValidationError("La cuenta está desactivada.")

        # Crear tokens JWT
        refresh = RefreshToken.for_user(user)

        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
            }
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
        fields = ['plan', 'precio', 'duracion', 'fecha_inicio', 'fecha_fin', 'activa']

# ----------------------------------------------------
# Serializer: PERFIL USUARIO (ENDPOINT PROTEGIDO)
# ----------------------------------------------------
class UserProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "rut",
            "telefono",
            "suscripcion_activa",
        ]
