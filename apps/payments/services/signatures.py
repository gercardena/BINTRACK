import hashlib
import hmac
import re

from rest_framework.exceptions import APIException

from .configuration import test_config


class InvalidNotification(APIException):
    status_code = 401
    default_detail = "Notificación no autenticada."
    default_code = "invalid_webhook_signature"


def verify_notification(request):
    config = test_config()
    data_id = request.query_params.get("data.id", "")
    request_id = request.headers.get("x-request-id", "")
    signature = request.headers.get("x-signature", "")
    if (len(request.query_params.getlist("data.id")) != 1
            or not re.fullmatch(r"[0-9]{1,100}", data_id)
            or not request_id or len(request_id) > 200 or any(c in request_id for c in ";:\r\n")
            or len(signature) > 1000):
        raise InvalidNotification()
    parts = {}
    for part in signature.split(","):
        key, separator, value = part.strip().partition("=")
        if not separator or key in parts:
            raise InvalidNotification()
        parts[key] = value
    if not re.fullmatch(r"[0-9]{10,13}", parts.get("ts", "")) or not re.fullmatch(r"[a-fA-F0-9]{64}", parts.get("v1", "")):
        raise InvalidNotification()
    manifest = f'id:{data_id};request-id:{request_id};ts:{parts["ts"]};'
    expected = hmac.new(config.webhook_secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, parts["v1"].lower()):
        raise InvalidNotification()
    # A delayed signed retry is safe because settlement is transactional/idempotent.
    body = request.data
    if (not isinstance(body, dict) or body.get("type") != "payment"
            or not isinstance(body.get("data"), dict) or str(body["data"].get("id")) != data_id
            or request.query_params.get("type", "payment") != "payment"):
        raise InvalidNotification()
    return data_id
