from django.conf import settings
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Payment
from .services.mercadopago import MercadoPagoService
from apps.accounts.services.subscriptions import activate_subscription_for_user


# ==============================
# Crear pago
# ==============================
class CrearPagoView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        amount = 10000  # CLP
        provider = "mercadopago"

        # Crear pago en BD
        payment = Payment.objects.create(
            user=user,
            amount=amount,
            provider=provider,
            status="pending",
        )

        # Crear preferencia Mercado Pago
        mp = MercadoPagoService()
        preference = mp.crear_preferencia(
            titulo="Suscripción BINTRACK",
            precio=amount,
            payment_id=payment.id,
        )

        # Guardar ID externo
        payment.external_id = preference.get("id")
        payment.save()

        # URL según entorno
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
# Confirmación manual
# No debe considerarse fuente definitiva
# ==============================
class ConfirmarPagoView(APIView):
    permission_classes = [AllowAny]  # MercadoPago no envía JWT

    def get(self, request):
        payment_id_mp = request.GET.get("payment_id")

        if not payment_id_mp:
            return Response(
                {"error": "payment_id no recibido"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        mp = MercadoPagoService()
        mp_payment = mp.consultar_pago(payment_id_mp)

        external_reference = mp_payment.get("external_reference")

        payment = get_object_or_404(
            Payment,
            id=external_reference,
        )

        status_mp = mp_payment.get("status")

        if status_mp == "approved":
            payment.status = "approved"
            activate_subscription_for_user(payment.user)
        elif status_mp == "rejected":
            payment.status = "rejected"
        else:
            payment.status = "pending"

        payment.save()

        return Response(
            {
                "payment_id": payment.id,
                "mercadopago_status": status_mp,
                "status": payment.status,
            },
            status=status.HTTP_200_OK,
        )


# ==============================
# Webhook MercadoPago
# Confirmación real y definitiva
# ==============================
@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def MercadoPagoWebhookView(request):
    topic = request.GET.get("topic")
    mp_id = request.GET.get("id")

    mp = MercadoPagoService()

    # Checkout Pro -> merchant_order
    if topic == "merchant_order":
        result = mp.sdk.merchant_order().get(mp_id)

        if result["status"] != 200:
            return Response(
                {"status": "order_not_found"},
                status=200,
            )

        order = result["response"]
        payments = order.get("payments", [])

        if not payments:
            return Response(
                {"status": "no_payments_yet"},
                status=200,
            )

        mp_payment_id = payments[0]["id"]

    # payment / payment.updated
    elif topic == "payment":
        mp_payment_id = mp_id

    else:
        return Response(
            {"status": "ignored"},
            status=200,
        )

    mp_payment = mp.consultar_pago(mp_payment_id)
    status_mp = mp_payment.get("status")

    external_reference = mp_payment.get("external_reference")

    if not external_reference:
        return Response(
            {"status": "no_reference"},
            status=200,
        )

    try:
        payment = Payment.objects.get(
            id=external_reference,
        )
    except Payment.DoesNotExist:
        return Response(
            {"status": "payment_not_found"},
            status=200,
        )

    if status_mp == "approved":
        payment.status = "approved"
        activate_subscription_for_user(payment.user)
    elif status_mp == "rejected":
        payment.status = "rejected"
    else:
        payment.status = "pending"

    payment.save()

    return Response(
        {
            "status": "ok",
            "payment_id": payment.id,
            "mercadopago_status": status_mp,
        },
        status=200,
    )


# ==============================
# Simulación de pago aprobado
# Solo desarrollo
# ==============================
class SimularPagoAprobadoView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, payment_id):
        if not settings.DEBUG:
            return Response(
                {
                    "error": "No disponible en producción",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        payment = get_object_or_404(
            Payment,
            id=payment_id,
            user=request.user,
        )

        payment.status = "approved"
        payment.save()

        user = payment.user
        activate_subscription_for_user(user)

        return Response(
            {
                "message": "Pago aprobado (simulado)",
                "payment_id": payment.id,
                "user_id": user.id,
                "suscripcion_activa": user.suscripcion_activa,
            },
            status=status.HTTP_200_OK,
        )