from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated

from .models import UserSubscription
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    UserSubscriptionSerializer
)


# ----------------------------------------------------
# Registro de usuario
# ----------------------------------------------------
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


# ----------------------------------------------------
# Login (JWT)
# ----------------------------------------------------
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)


# ----------------------------------------------------
# Paso 5: Consultar estado de suscripción
# ----------------------------------------------------
class SubscriptionStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            suscripcion = UserSubscription.objects.get(usuario=request.user, activa=True)
        except UserSubscription.DoesNotExist:
            return Response({
                "suscrito": False,
                "mensaje": "El usuario NO tiene una suscripción activa"
            })

        serializer = UserSubscriptionSerializer(suscripcion)

        return Response({
            "suscrito": True,
            "detalle": serializer.data
        })