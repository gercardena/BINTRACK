"""Temporary localhost-only gateway. Never tunnel Django's port directly.

Only the payment webhook is forwarded. Browser return pages are static and do
not confirm payments. No request bodies, secrets, or backend errors are logged.
Run with --tunnel to own an ngrok child with an automatic 90-minute expiry.
"""
import argparse
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import shutil
import socket
import subprocess
import threading
import time
from urllib.parse import urlsplit

WEBHOOK = '/api/payments/webhook/'
RETURNS = {'/mp-test/success', '/mp-test/failure', '/mp-test/pending'}
MAX_BODY = 65536


def diagnostic(event, status=0):
    # Callers supply fixed event names and numeric codes, never request data.
    print(json.dumps({'time_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                      'component': 'gateway', 'event': event, 'status': int(status)}), flush=True)


class Gateway(BaseHTTPRequestHandler):
    server_version = 'TestGateway'
    sys_version = ''

    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def log_message(self, *args):
        pass

    def reply(self, status, message):
        diagnostic('response', status)
        data = json.dumps({'message': message}).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Connection', 'close')
        self.end_headers()
        self.wfile.write(data)
        self.close_connection = True

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == '/mp-test/health':
            return self.reply(200, 'BINTRACK: receptor temporal de prueba disponible.')
        if path in RETURNS:
            return self.reply(200, 'Retorno de prueba recibido. Esto NO confirma el pago ni activa una suscripcion. Vuelve a BINTRACK para verificarlo.')
        self.reply(404, 'Ruta no disponible.')

    def do_POST(self):
        # Exact raw path: encoded paths, traversal and other API endpoints fail closed.
        if len(self.path) > 2048 or self.path.split('?', 1)[0] != WEBHOOK:
            return self.reply(404, 'Ruta no disponible.')
        lengths = self.headers.get_all('Content-Length', [])
        if self.headers.get('Transfer-Encoding') or len(lengths) != 1:
            return self.reply(400, 'Formato no permitido.')
        try:
            length = int(lengths[0])
        except ValueError:
            return self.reply(400, 'Formato no permitido.')
        if not 0 < length <= MAX_BODY:
            return self.reply(413, 'Tamano no permitido.')
        if self.headers.get_content_type() != 'application/json':
            return self.reply(415, 'Se requiere JSON.')
        try:
            body = self.rfile.read(length)
            if len(body) != length or not isinstance(json.loads(body), dict):
                return self.reply(400, 'JSON no valido.')
        except (ValueError, OSError):
            return self.reply(400, 'JSON no valido.')
        headers = {'Content-Type': 'application/json'}
        for name in ('x-signature', 'x-request-id'):
            values = self.headers.get_all(name, [])
            if len(values) != 1 or len(values[0]) > 1000:
                return self.reply(401, 'Notificacion no autenticada.')
            headers[name] = values[0]
        upstream = http.client.HTTPConnection('127.0.0.1', 8000, timeout=10)
        try:
            upstream.request('POST', self.path, body=body, headers=headers)
            response = upstream.getresponse()
            # Never relay Django debug pages, cookies, redirects or private data.
            status = response.status
            diagnostic('backend_response', status)
            if status not in (200, 400, 401, 403, 404, 409, 429, 503):
                status = 503
        except (OSError, http.client.HTTPException):
            diagnostic('backend_unreachable')
            status = 503
        finally:
            upstream.close()
        self.reply(status, 'Notificacion recibida.' if status == 200 else 'Notificacion no confirmada.')


class LimitedServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, *args, **kwargs):
        self.slots = threading.BoundedSemaphore(8)
        super().__init__(*args, **kwargs)

    def process_request(self, request, address):
        if not self.slots.acquire(blocking=False):
            diagnostic('capacity_exceeded')
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, address)
        except Exception:
            self.slots.release()
            raise

    def process_request_thread(self, request, address):
        try:
            super().process_request_thread(request, address)
        finally:
            self.slots.release()

    def handle_error(self, request, address):
        diagnostic('request_exception')


def tunnel_url():
    conn = http.client.HTTPConnection('127.0.0.1', 4040, timeout=2)
    try:
        conn.request('GET', '/api/tunnels')
        data = json.loads(conn.getresponse().read(65536))
        for tunnel in data.get('tunnels', []):
            if (tunnel.get('config', {}).get('addr') == 'http://127.0.0.1:8765'
                    and tunnel.get('public_url', '').startswith('https://')):
                return tunnel['public_url']
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tunnel', action='store_true')
    parser.add_argument('--minutes', type=int, default=90)
    args = parser.parse_args()
    if not 1 <= args.minutes <= 90:
        parser.error('Duration must be between 1 and 90 minutes.')
    child = None
    if args.tunnel:
        with socket.socket() as probe:
            if probe.connect_ex(('127.0.0.1', 4040)) == 0:
                raise SystemExit('An ngrok agent is already running; nothing started.')
        executable = shutil.which('ngrok')
        if not executable:
            raise SystemExit('ngrok is not installed; nothing started.')
    server = LimitedServer(('127.0.0.1', 8765), Gateway)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    deadline = time.monotonic() + args.minutes * 60
    print('GATEWAY_READY=127.0.0.1:8765', flush=True)
    try:
        if args.tunnel:
            child = subprocess.Popen(
                [executable, 'http', 'http://127.0.0.1:8765', '--inspect=false', '--log=false'],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
            )
            print('NGROK_PID=' + str(child.pid), flush=True)
            url = None
            for _ in range(30):
                if child.poll() is not None:
                    break
                try:
                    url = tunnel_url()
                except (OSError, ValueError, http.client.HTTPException):
                    pass
                if url:
                    break
                time.sleep(1)
            if not url:
                print('TUNNEL_NOT_READY: check ngrok account configuration locally.', flush=True)
                return
            print('PUBLIC_URL=' + url, flush=True)
            print('AUTO_CLOSE_MINUTES=' + str(args.minutes), flush=True)
        while time.monotonic() < deadline:
            if child and child.poll() is not None:
                break
            time.sleep(1)
    finally:
        if child and child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=5)
        server.shutdown()
        server.server_close()
        print('GATEWAY_CLOSED', flush=True)


if __name__ == '__main__':
    main()
