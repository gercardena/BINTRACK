from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated

from apps.accounts.services.users import get_usuario_titular
from apps.accounts.services.subscription_access import subscription_access

from .models import UserSubscription
from .serializers import (
    LoginSerializer,
    UserSubscriptionSerializer,
)

from .serializers import UserProfileSerializer


# ----------------------------------------------------
# Registro de usuario
# ----------------------------------------------------
class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        return Response(
            {
                "detail": (
                    "El registro de usuarios desde la app está deshabilitado. "
                    "Solicita la creación de usuario al administrador."
                )
            },
            status=status.HTTP_403_FORBIDDEN,
        )


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
# Consultar estado de suscripción
# ----------------------------------------------------
class SubscriptionStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        titular = get_usuario_titular(
            request.user,
        )

        suscripcion = UserSubscription.objects.filter(usuario=titular).first()
        acceso = subscription_access(suscripcion)
        return Response({
            "suscrito": acceso["estado"] == "activa",
            "detalle": UserSubscriptionSerializer(suscripcion).data if suscripcion else None,
            "suscripcion_acceso": acceso,
        })


# ----------------------------------------------------
# PERFIL USUARIO (endpoint protegido real)
# ----------------------------------------------------
class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        titular = get_usuario_titular(
            request.user,
        )

        serializer = UserProfileSerializer(
            request.user,
            context={
                "request": request,
                "titular": titular,
            },
        )

        return Response(serializer.data)
