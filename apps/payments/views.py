from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
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
