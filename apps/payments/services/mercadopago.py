import mercadopago
from django.conf import settings


class MercadoPagoService:
    def __init__(self):
        self.sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)

    def crear_preferencia(self, *, titulo, precio, user_id):
        preference_data = {
            "items": [
                {
                    "title": titulo,
                    "quantity": 1,
                    "unit_price": float(precio),
                    "currency_id": "CLP",
                }
            ],
            "metadata": {
                "user_id": user_id
            },
        }

        result = self.sdk.preference().create(preference_data)

        if result["status"] not in (200, 201):
            raise Exception(f"Error MercadoPago: {result}")

        return result["response"]