from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import User, UsuarioAsociado


class StrictSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if not isinstance(data, dict):
            raise serializers.ValidationError("Se esperaba un objeto de datos.")
        extra = set(data) - set(self.fields)
        if extra:
            raise serializers.ValidationError({key: "Este campo no se puede modificar." for key in extra})
        return super().to_internal_value(data)


class SecondaryCreateSerializer(StrictSerializer):
    username = serializers.CharField(max_length=150, validators=[UnicodeUsernameValidator()])
    email = serializers.EmailField(max_length=254)
    first_name = serializers.CharField(max_length=150, allow_blank=True, required=False)
    last_name = serializers.CharField(max_length=150, allow_blank=True, required=False)
    telefono = serializers.CharField(max_length=20, allow_blank=True, required=False)
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("Ese nombre de usuario no está disponible.")
        return value

    def validate_email(self, value):
        value = value.lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Ese correo ya está registrado.")
        return value

    def validate_password(self, value):
        if value != value.strip():
            raise serializers.ValidationError("No uses espacios al inicio o al final de la contraseña.")
        return value

    def validate(self, attrs):
        try:
            validate_password(attrs["password"], User(**{k: v for k, v in attrs.items() if k != "password"}))
        except DjangoValidationError as error:
            raise serializers.ValidationError({"password": list(error.messages)})
        return attrs


class SecondaryUpdateSerializer(StrictSerializer):
    email = serializers.EmailField(max_length=254, required=False)
    first_name = serializers.CharField(max_length=150, allow_blank=True, required=False)
    last_name = serializers.CharField(max_length=150, allow_blank=True, required=False)
    telefono = serializers.CharField(max_length=20, allow_blank=True, required=False)
    activo = serializers.BooleanField(required=False)

    def validate_email(self, value):
        value = value.lower()
        user = self.context["secondary"]
        if User.objects.filter(email__iexact=value).exclude(pk=user.pk).exists():
            raise serializers.ValidationError("Ese correo ya está registrado.")
        return value


class SecondarySerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="usuario_asociado_id")
    username = serializers.CharField(source="usuario_asociado.username")
    email = serializers.CharField(source="usuario_asociado.email")
    first_name = serializers.CharField(source="usuario_asociado.first_name")
    last_name = serializers.CharField(source="usuario_asociado.last_name")
    telefono = serializers.CharField(source="usuario_asociado.telefono", allow_null=True)
    activo = serializers.SerializerMethodField()

    def get_activo(self, relation):
        return relation.activo and relation.usuario_asociado.is_active

    class Meta:
        model = UsuarioAsociado
        fields = ["id", "user_id", "username", "email", "first_name", "last_name", "telefono", "activo", "fecha_creacion"]
        read_only_fields = fields
