import http.client
import threading
import unittest
import json
from unittest.mock import patch, MagicMock

from scripts.mp_test_gateway import Gateway, LimitedServer


class GatewayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = LimitedServer(('127.0.0.1', 0), Gateway)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def request(self, method, path, body=None, headers=None):
        # Capture the real class before mocking the gateway's outgoing connection.
        conn = self.real_connection('127.0.0.1', self.server.server_port, timeout=3)
        conn.request(method, path, body=body, headers=headers or {})
        response = conn.getresponse()
        status, data = response.status, response.read()
        conn.close()
        return status, data

    def setUp(self):
        self.real_connection = http.client.HTTPConnection
        self.log_patch = patch('builtins.print')
        self.logged = self.log_patch.start()
        self.addCleanup(self.log_patch.stop)

    def test_diagnostics_do_not_include_request_secrets(self):
        self.request('GET', '/mp-test/success?token=PRIVATE', headers={
            'Authorization': 'Bearer PRIVATE', 'Cookie': 'PRIVATE'})
        records = [json.loads(call.args[0]) for call in self.logged.call_args_list]
        self.assertTrue(records)
        for record in records:
            self.assertEqual(set(record), {'time_utc', 'component', 'event', 'status'})
            self.assertNotIn('PRIVATE', str(record))

    def test_receiver_diagnostics_omit_request_details(self):
        from scripts.mp_test_receiver import QuietHandler
        QuietHandler.log_request(None, 401, 'PRIVATE')
        record = json.loads(self.logged.call_args.args[0])
        self.assertEqual(record['component'], 'receiver')
        self.assertEqual(record['status'], 401)
        self.assertNotIn('PRIVATE', str(record))

    def test_block_other_routes(self):
        with patch('scripts.mp_test_gateway.http.client.HTTPConnection') as upstream:
            for path in ('/', '/admin/', '/.env', '/api/accounts/',
                         '/api/payments/crear/', '/api/payments/webhook/../crear/',
                         '/api/payments/%77ebhook/'):
                for method in ('GET', 'POST'):
                    self.assertEqual(self.request(method, path)[0], 404)
            upstream.assert_not_called()

    def test_static_returns_do_not_forward_or_echo_query(self):
        with patch('scripts.mp_test_gateway.http.client.HTTPConnection') as upstream:
            for path in ('/mp-test/success', '/mp-test/failure', '/mp-test/pending', '/mp-test/health'):
                status, body = self.request('GET', path + '?token=PRIVATE&status=approved')
                self.assertEqual(status, 200)
                self.assertNotIn(b'PRIVATE', body)
            upstream.assert_not_called()

    def test_unsigned_body_is_rejected_before_backend(self):
        with patch('scripts.mp_test_gateway.http.client.HTTPConnection') as upstream:
            self.assertEqual(self.request('POST', '/api/payments/webhook/', '{}',
                                         {'Content-Type': 'application/json'})[0], 401)
            upstream.assert_not_called()

    def test_invalid_content_and_size(self):
        with patch('scripts.mp_test_gateway.http.client.HTTPConnection') as upstream:
            for body, headers, expected in (
                ('{}', {'Content-Type': 'text/plain'}, 415),
                ('bad', {'Content-Type': 'application/json'}, 400),
                ('[]', {'Content-Type': 'application/json'}, 400),
                ('x' * 65537, {'Content-Type': 'application/json'}, 413),
                ('{}', {'Content-Type': 'application/json', 'Transfer-Encoding': 'chunked'}, 400),
            ):
                self.assertEqual(self.request('POST', '/api/payments/webhook/', body, headers)[0], expected)
            upstream.assert_not_called()

    def test_forward_only_signature_headers_to_fixed_backend(self):
        connection = MagicMock()
        connection.getresponse.return_value.status = 200
        with patch('scripts.mp_test_gateway.http.client.HTTPConnection', return_value=connection) as factory:
            status, body = self.request('POST', '/api/payments/webhook/?data.id=123&type=payment', '{}', {
                'Content-Type': 'application/json', 'x-signature': 'signed',
                'x-request-id': 'request', 'Authorization': 'Bearer PRIVATE',
                'Cookie': 'session=PRIVATE', 'Host': 'external.example',
            })
            self.assertEqual(status, 200)
            factory.assert_called_once_with('127.0.0.1', 8000, timeout=10)
            forwarded = connection.request.call_args.kwargs['headers']
            self.assertEqual(set(forwarded), {'Content-Type', 'x-signature', 'x-request-id'})
            self.assertNotIn(b'PRIVATE', body)

    def test_backend_debug_error_and_redirect_never_exposed(self):
        for upstream_status in (500, 302, 401, 503):
            connection = MagicMock()
            connection.getresponse.return_value.status = upstream_status
            connection.getresponse.return_value.read.return_value = b'PRIVATE DEBUG SECRET'
            with patch('scripts.mp_test_gateway.http.client.HTTPConnection', return_value=connection):
                status, body = self.request('POST', '/api/payments/webhook/', '{}', {
                    'Content-Type': 'application/json', 'x-signature': 'signed', 'x-request-id': 'request',
                })
                self.assertEqual(status, upstream_status if upstream_status in (401, 503) else 503)
                self.assertNotIn(b'PRIVATE', body)

    def test_backend_offline_returns_safe_retry_status(self):
        connection = MagicMock()
        connection.request.side_effect = ConnectionRefusedError()
        with patch('scripts.mp_test_gateway.http.client.HTTPConnection', return_value=connection):
            self.assertEqual(self.request('POST', '/api/payments/webhook/', '{}', {
                'Content-Type': 'application/json', 'x-signature': 'signed', 'x-request-id': 'request',
            })[0], 503)


if __name__ == '__main__':
    unittest.main()
