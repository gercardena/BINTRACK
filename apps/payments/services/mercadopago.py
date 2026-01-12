import mercadopago
from django.conf import settings


class MercadoPagoService:
    def __init__(self):
        self.sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)

    def crear_preferencia(self, *, titulo, precio, payment_id):
        preference_data = {
            "items": [
                {
                    "title": titulo,
                    "quantity": 1,
                    "unit_price": float(precio),
                    "currency_id": "CLP",
                }
            ],

            # 🔥 RELACIÓN REAL CON TU BD
            "external_reference": str(payment_id),

            # 🔥 WEBHOOK REAL
            "notification_url": settings.MERCADOPAGO_NOTIFICATION_URL,
        }

        result = self.sdk.preference().create(preference_data)

        if result["status"] not in (200, 201):
            raise Exception(f"Error MercadoPago: {result}")

        return result["response"]

    def consultar_pago(self, payment_id):
        result = self.sdk.payment().get(payment_id)

        if result["status"] != 200:
            raise Exception(f"Error consultando pago MercadoPago: {result}")

        return result["response"]