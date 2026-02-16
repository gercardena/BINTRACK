from rest_framework import serializers
from .models import BinType
from .models import Cliente, BinMovement


# -------------------------------------
# Serializer BinType (simple)
# -------------------------------------
class BinTypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = BinType
        fields = "__all__"

class ClienteSerializer(serializers.ModelSerializer):

    class Meta:
        model = Cliente
        fields = "__all__"

class BinMovementSerializer(serializers.ModelSerializer):

    class Meta:
        model = BinMovement
        fields = "__all__"