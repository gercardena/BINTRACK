"""Fail closed: these endpoints can only use explicitly enabled test credentials."""
from dataclasses import dataclass, field
from urllib.parse import urlsplit
import re

from django.conf import settings
from rest_framework.exceptions import APIException


class PaymentsUnavailable(APIException):
    status_code = 503
    default_detail = "Los pagos de prueba no están disponibles. No se ha confirmado ningún cobro."
    default_code = "payments_unavailable"


class PaymentConflict(APIException):
    status_code = 409
    default_detail = "Existe un pago pendiente de revisión. No generes otro pago para el mismo período."
    default_code = "payment_requires_review"


def https_url(value):
    try:
        url = urlsplit(value)
        return bool(url.scheme == "https" and url.hostname and not url.username and not url.password)
    except (ValueError, TypeError):
        return False


@dataclass(frozen=True)
class TestConfig:
    token: str = field(repr=False)
    collector_id: str
    webhook_secret: str = field(repr=False)


def test_config():
    token = getattr(settings, "MERCADOPAGO_TEST_ACCESS_TOKEN", "")
    collector = str(getattr(settings, "MERCADOPAGO_TEST_COLLECTOR_ID", ""))
    secret = getattr(settings, "MERCADOPAGO_TEST_WEBHOOK_SECRET", "")
    if (not getattr(settings, "MERCADOPAGO_TEST_ENABLED", False)
            or getattr(settings, "MERCADOPAGO_ENV", "") != "sandbox"
            or not token or not secret or not re.fullmatch(r"[0-9]{1,30}", collector)):
        raise PaymentsUnavailable()
    return TestConfig(token, collector, secret)


def preference_urls():
    notification = getattr(settings, "MERCADOPAGO_TEST_NOTIFICATION_URL", "")
    back_urls = {key: getattr(settings, f"MERCADOPAGO_TEST_{key.upper()}_URL", "")
                 for key in ("success", "failure", "pending")}
    if not all(https_url(url) for url in [notification, *back_urls.values()]):
        raise PaymentsUnavailable("Configura las direcciones HTTPS de prueba antes de crear un enlace.")
    if urlsplit(notification).hostname in ("localhost", "127.0.0.1", "::1"):
        raise PaymentsUnavailable("Las notificaciones requieren una dirección HTTPS pública de prueba.")
    return notification, back_urls
