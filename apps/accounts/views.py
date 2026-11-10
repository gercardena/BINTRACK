from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated

from apps.accounts.services.users import get_usuario_titular
from apps.accounts.services.subscription_access import subscription_access

from .models import UserSubscription
from .serializers import (
    ChangePasswordSerializer,
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


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.set_password(serializer.validated_data["nueva_contrasena"])
        user.debe_cambiar_contrasena = False
        user.save(update_fields=["password", "debe_cambiar_contrasena"])

        return Response({
            "detail": "Contraseña actualizada correctamente.",
        })
