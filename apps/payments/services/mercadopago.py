import re
from urllib.parse import urlsplit

import mercadopago
from mercadopago.config import RequestOptions

from .configuration import PaymentsUnavailable, https_url, preference_urls, test_config


class MercadoPagoService:
    def __init__(self):
        self.config = test_config()
        self.sdk = mercadopago.SDK(
            self.config.token,
            request_options=RequestOptions(connection_timeout=8.0, max_retries=0),
        )

    @staticmethod
    def _request(call, accepted=(200,)):
        # Provider errors can contain tokens/personal data: never echo the response.
        try:
            result = call()
        except Exception:
            raise PaymentsUnavailable("No se pudo consultar Mercado Pago. El estado queda pendiente.") from None
        if (not isinstance(result, dict) or result.get("status") not in accepted
                or not isinstance(result.get("response"), dict)):
            raise PaymentsUnavailable("Mercado Pago no confirmó la solicitud. Revisa el estado antes de reintentar.")
        return result["response"]

    def verificar_vendedor_prueba(self):
        seller = self._request(lambda: self.sdk.user().get())
        if (str(seller.get("id")) != self.config.collector_id
                or "test_user" not in (seller.get("tags") or [])
                or seller.get("country_id") != "CL"):
            raise PaymentsUnavailable("Se requiere una cuenta vendedora de prueba de Chile verificada.")

    def crear_preferencia(self, payment):
        notification, back_urls = preference_urls()
        self.verificar_vendedor_prueba()
        payload = {
            "items": [{"id": payment.plan_code, "title": "Suscripción mensual BINTRACK (PRUEBA)",
                       "quantity": 1, "unit_price": payment.amount, "currency_id": "CLP"}],
            "external_reference": str(payment.reference),
            "notification_url": notification,
            "back_urls": back_urls,
            "auto_return": "approved",
            "expires": True,
            "expiration_date_from": payment.created_at.isoformat(),
            "expiration_date_to": payment.expires_at.isoformat(),
        }
        options = RequestOptions(
            access_token=self.config.token, connection_timeout=8.0, max_retries=0,
            custom_headers={"x-idempotency-key": str(payment.reference)},
        )
        preference = self._request(lambda: self.sdk.preference().create(payload, options), (200, 201))
        checkout = preference.get("init_point", "")
        if (not preference.get("id") or not https_url(checkout)
                or urlsplit(checkout).hostname not in ("www.mercadopago.cl", "mercadopago.cl", "sandbox.mercadopago.cl")):
            raise PaymentsUnavailable("Mercado Pago no devolvió un enlace de prueba válido para Chile.")
        return {"id": str(preference["id"]), "init_point": checkout}

    def consultar_pago(self, payment_id):
        if not re.fullmatch(r"[0-9]{1,100}", str(payment_id)):
            raise PaymentsUnavailable("Identificador de pago inválido.")
        return self._request(lambda: self.sdk.payment().get(str(payment_id)))
