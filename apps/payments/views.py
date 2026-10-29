import re

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError

from apps.accounts.permissions.account_owner import IsAccountOwner
from .models import Payment
from .services.checkout import create_checkout
from .services.mercadopago import MercadoPagoService
from .services.reconciliation import reconcile
from .services.signatures import verify_notification


def payment_data(payment):
    usable_link = (payment.environment == "sandbox" and not payment.applied_at
                   and not payment.needs_review and payment.expires_at
                   and payment.expires_at > timezone.now()
                   and payment.status in {"pending", "rejected"})
    return {
        "payment_id": payment.pk,
        "status": payment.status,
        "amount": payment.amount,
        "currency": "CLP",
        "environment": payment.environment or "legacy",
        "init_point": payment.checkout_url if usable_link else None,
        "expires_at": payment.expires_at,
        "applied": payment.applied_at is not None,
        "applied_until": payment.applied_until,
        "needs_review": payment.needs_review,
        "review_reason": payment.review_reason,
    }


class CrearPagoView(APIView):
    permission_classes = [IsAuthenticated, IsAccountOwner]

    def post(self, request):
        if request.data:
            raise ValidationError("El importe, plan y período se calculan en el servidor; no envíes esos campos.")
        payment, created = create_checkout(request.user)
        return Response(payment_data(payment), status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class ConfirmarPagoView(APIView):
    """Read-only polling. A browser redirect is never evidence of payment."""
    permission_classes = [IsAuthenticated, IsAccountOwner]

    def get(self, request):
        local_id = request.query_params.get("payment_id", "")
        if not re.fullmatch(r"[0-9]{1,18}", local_id):
            raise ValidationError("Indica el identificador local de la orden.")
        payment = get_object_or_404(Payment, pk=local_id, user=request.user)
        return Response(payment_data(payment))


class VerificarPagoView(APIView):
    """Authenticated reconciliation for tests/missed webhooks, using the same checks."""
    permission_classes = [IsAuthenticated, IsAccountOwner]

    def post(self, request, payment_id):
        payment = get_object_or_404(Payment, pk=payment_id, user=request.user)
        if not isinstance(request.data, dict) or set(request.data) != {"provider_payment_id"}:
            raise ValidationError("Indica únicamente provider_payment_id.")
        provider_id = str(request.data["provider_payment_id"])
        if not re.fullmatch(r"[0-9]{1,100}", provider_id):
            raise ValidationError("Identificador del proveedor inválido.")
        data = MercadoPagoService().consultar_pago(provider_id)
        payment = reconcile(provider_id, data, expected_order=payment)
        return Response(payment_data(payment))


class MercadoPagoWebhookAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []  # HMAC, not a browser/JWT, authenticates notifications.

    def post(self, request):
        provider_id = verify_notification(request)
        data = MercadoPagoService().consultar_pago(provider_id)
        payment = reconcile(provider_id, data)
        return Response({"status": "ok", "requires_review": payment.needs_review})


MercadoPagoWebhookView = MercadoPagoWebhookAPIView.as_view()


class SimularPagoAprobadoView(APIView):
    permission_classes = [IsAuthenticated, IsAccountOwner]

    def post(self, request, payment_id):
        # Do not resurrect the old DEBUG shortcut: unit tests mock provider data.
        return Response({"detail": "La activación simulada fue retirada. Usa las pruebas aisladas."}, status=410)
