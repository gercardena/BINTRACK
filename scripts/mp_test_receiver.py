"""Bounded local webhook receiver; enables sandbox only inside this process.

The .env stays disabled. This is a temporary test utility, not a production server.
Only the webhook route is served, even when accessed through localhost.
"""
import argparse
import os
from pathlib import Path
import sys
import threading
import json
import time
from wsgiref.simple_server import make_server, WSGIRequestHandler


class QuietHandler(WSGIRequestHandler):
    def log_request(self, code='-', size='-'):
        # Omit URL, query, remote address, headers, body and exception text.
        status = int(code) if str(code).isdigit() else 0
        print(json.dumps({'time_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                          'component': 'receiver', 'event': 'response',
                          'status': status}), flush=True)

    def log_message(self, *args):
        pass

    def get_stderr(self):
        # Do not print request details or tracebacks from this public test receiver.
        return self.server.private_errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--minutes', type=int, default=60)
    parser.add_argument('--test-buyer-id', default='',
                        help='Explicitly authorized test buyer; enables the scoped live_mode exception only in this process.')
    args = parser.parse_args()
    if not 1 <= args.minutes <= 90:
        parser.error('Duration must be 1 to 90 minutes.')
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
    import django
    django.setup()
    from django.conf import settings
    from django.db import connection
    from django.core.wsgi import get_wsgi_application
    from apps.accounts.models import User
    from apps.accounts.permissions.account_owner import es_titular
    from apps.payments.services.configuration import test_config
    from apps.payments.services.mercadopago import MercadoPagoService

    assert connection.vendor == 'postgresql'
    assert connection.settings_dict.get('HOST') in ('localhost', '127.0.0.1', '::1')
    assert settings.MERCADOPAGO_ENV == 'sandbox'
    owner = User.objects.get(username='mp_prueba_local')
    assert es_titular(owner) and not owner.is_staff and not owner.is_superuser
    settings.DEBUG = False
    settings.ALLOWED_HOSTS = ['127.0.0.1', 'localhost']
    settings.MERCADOPAGO_TEST_ENABLED = True
    if args.test_buyer_id:
        if not args.test_buyer_id.isascii() or not args.test_buyer_id.isdigit() or len(args.test_buyer_id) > 30:
            raise ValueError('Invalid test buyer identifier')
        settings.MERCADOPAGO_TEST_ALLOW_TEST_USERS_LIVE_MODE = True
        settings.MERCADOPAGO_TEST_BUYER_ID = args.test_buyer_id
        settings.MERCADOPAGO_TEST_LOCAL_OWNER_ID = str(owner.pk)
    else:
        settings.MERCADOPAGO_TEST_ALLOW_TEST_USERS_LIVE_MODE = False
    test_config()
    MercadoPagoService().verificar_vendedor_prueba()
    application = get_wsgi_application()

    def only_webhook(environ, start_response):
        if environ.get('PATH_INFO') != '/api/payments/webhook/' or environ.get('REQUEST_METHOD') != 'POST':
            body = b'{"detail":"Route unavailable"}'
            start_response('404 Not Found', [('Content-Type', 'application/json'), ('Content-Length', str(len(body)))])
            return [body]
        return application(environ, start_response)

    with open(os.devnull, 'w') as errors:
        with make_server('127.0.0.1', 8000, only_webhook, handler_class=QuietHandler) as server:
            server.private_errors = errors
            timer = threading.Timer(args.minutes * 60, server.shutdown)
            timer.daemon = True
            timer.start()
            print('LOCAL_TEST_WEBHOOK_READY=127.0.0.1:8000', flush=True)
            print('AUTO_CLOSE_MINUTES=' + str(args.minutes), flush=True)
            print('SCOPED_TEST_EXCEPTION=' + str(bool(args.test_buyer_id)), flush=True)
            try:
                server.serve_forever()
            finally:
                timer.cancel()
                print('LOCAL_TEST_WEBHOOK_CLOSED', flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        print('RECEIVER_START_FAILED; private details omitted.', flush=True)
        sys.exit(1)
