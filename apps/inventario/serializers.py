from rest_framework import serializers
from .models import Inventory


class InventorySerializer(serializers.Serializer):

    bin_type_id = serializers.IntegerField()

    bin_nombre = serializers.CharField()

    entradas = serializers.IntegerField()

    prestamos = serializers.IntegerField()

    devoluciones = serializers.IntegerField()

    bajas = serializers.IntegerField()

    disponible = serializers.IntegerField()

