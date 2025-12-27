from django.conf import settings
from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status

from .models import Payment
from .services.mercadopago import MercadoPagoService


class CrearPagoView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        amount = 10000  # CLP
        provider = "mercadopago"

        # 1️⃣ Crear pago en BD
        payment = Payment.objects.create(
            user=user,
            amount=amount,
            provider=provider,
            status="pending",
        )

        # 2️⃣ Crear preferencia Mercado Pago
        mp = MercadoPagoService()
        preference = mp.crear_preferencia(
            titulo="Suscripción BINTRACK",
            precio=amount,
            user_id=user.id,
        )

        # 3️⃣ Guardar ID externo
        payment.external_id = preference.get("id")
        payment.save()

        # 4️⃣ URL correcta según entorno
        init_point = (
            preference.get("sandbox_init_point")
            if settings.DEBUG
            else preference.get("init_point")
        )

        return Response(
            {
                "payment_id": payment.id,
                "init_point": init_point,
            },
            status=status.HTTP_201_CREATED,
        )


# ==============================
# NUEVA VISTA — Paso 6.4.3
# ==============================

class ConfirmarPagoView(APIView):
    permission_classes = [AllowAny]  # MercadoPago NO envía JWT

    def get(self, request):
        payment_id_mp = request.GET.get("payment_id")

        if not payment_id_mp:
            return Response(
                {"error": "payment_id no recibido"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        mp = MercadoPagoService()
        mp_payment = mp.consultar_pago(payment_id_mp)

        status_mp = mp_payment.get("status")

        # Buscar el pago en nuestra BD
        payment = get_object_or_404(
            Payment,
            external_id=payment_id_mp
        )

        # Mapear estado MercadoPago → BD
        if status_mp == "approved":
            payment.status = "approved"
        elif status_mp == "pending":
            payment.status = "pending"
        else:
            payment.status = "rejected"

        payment.save()

        return Response(
            {
                "payment_id": payment.id,
                "mercadopago_status": status_mp,
                "status": payment.status,
            },
            status=status.HTTP_200_OK,
        )
