from rest_framework import serializers
from django.contrib.auth import authenticate
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
        user.suscripcion_activa = False  # El usuario inicia sin suscripción activa
        user.save()

        # ❗ NO crear suscripción aquí
        # La suscripción se activará una vez que pague.

        return user


# ----------------------------------------------------
# Serializer: LOGIN
# ----------------------------------------------------
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get("email")
        password = data.get("password")

        user = authenticate(username=email, password=password)

        if not user:
            raise serializers.ValidationError("Credenciales inválidas")

        data["user"] = user
        return data


# ----------------------------------------------------
# Serializer: CONSULTAR ESTADO DE SUSCRIPCIÓN
# ----------------------------------------------------
class UserSubscriptionSerializer(serializers.ModelSerializer):
    plan = serializers.CharField(source="plan.nombre")
    precio = serializers.IntegerField(source="plan.precio")
    duracion = serializers.IntegerField(source="plan.duracion_dias")

    class Meta:
        model = UserSubscription
        fields = ['plan', 'precio', 'duracion', 'fecha_inicio', 'fecha_fin', 'activa']
