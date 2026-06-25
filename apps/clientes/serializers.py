import re

from rest_framework import serializers

from .models import Client


def normalizar_rut(value):
    rut = str(value or "").strip().upper()
    rut = rut.replace(".", "").replace(" ", "")

    if "-" not in rut and len(rut) > 1:
        rut = f"{rut[:-1]}-{rut[-1]}"

    return rut


def rut_valido(value):
    rut = normalizar_rut(value)

    if not re.match(r"^\d{7,8}-[\dK]$", rut):
        return False

    cuerpo, dv = rut.split("-")

    suma = 0
    multiplo = 2

    for numero in reversed(cuerpo):
        suma += int(numero) * multiplo
        multiplo += 1

        if multiplo > 7:
            multiplo = 2

    resto = suma % 11
    esperado = 11 - resto

    if esperado == 11:
        dv_esperado = "0"
    elif esperado == 10:
        dv_esperado = "K"
    else:
        dv_esperado = str(esperado)

    return dv == dv_esperado


class ClientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Client
        fields = "__all__"
        read_only_fields = [
            "usuario",
            "fecha_creacion",
        ]

    def validate_nombre(self, value):
        value = str(value or "").strip()

        if not value:
            raise serializers.ValidationError(
                "El nombre es obligatorio."
            )

        return value

    def validate_rut(self, value):
        rut = normalizar_rut(value)

        if not rut_valido(rut):
            raise serializers.ValidationError(
                "El RUT no es válido."
            )

        request = self.context.get("request")

        if request is not None:
            queryset = Client.objects.filter(
                usuario=request.user,
                rut=rut,
            )

            if self.instance is not None:
                queryset = queryset.exclude(
                    pk=self.instance.pk,
                )

            if queryset.exists():
                raise serializers.ValidationError(
                    "Ya existe un cliente con este RUT."
                )

        return rut

    def validate_email(self, value):
        if value in ["", None]:
            return None

        return value

    def validate_telefono(self, value):
        if value in ["", None]:
            return None

        return str(value).strip()

    def validate_direccion(self, value):
        if value in ["", None]:
            return None

        return str(value).strip()