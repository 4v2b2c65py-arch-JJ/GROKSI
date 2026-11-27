import json
import os
import socket
import sys
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

UPSTREAM = "https://api.x.ai"
HOST = "0.0.0.0"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
XAPI_KEY = os.environ.get("XAPI") or os.environ.get("XAI_API_KEY")

if not XAPI_KEY:
    sys.exit("ERROR: XAPI/XAI_API_KEY not set. Run: export XAPI=xai-...")


def local_endpoints():
    found = []
    try:
        host = socket.gethostname()
        for info in socket.getaddrinfo(host, None):
            ip = info[4][0]
            if ip not in found and not ip.startswith("127."):
                found.append(ip)
    except socket.error:
        pass
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            if ip not in found:
                found.append(ip)
    except OSError:
        pass
    return found


class Handler(BaseHTTPRequestHandler):
    def _forward(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else None
        url = UPSTREAM + self.path
        req = urllib.request.Request(url, data=body, method=self.command)
        for k, v in self.headers.items():
            if k.lower() not in ("host", "content-length", "connection", "authorization"):
                req.add_header(k, v)
        req.add_header("Authorization", f"Bearer {XAPI_KEY}")
        try:
            with urllib.request.urlopen(req) as r:
                self.send_response(r.status)
                for k, v in r.getheaders():
                    if k.lower() not in ("transfer-encoding", "connection", "content-encoding"):
                        self.send_header(k, v)
                data = r.read()
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
        except urllib.error.HTTPError as e:
            data = e.read()
            self.send_response(e.code)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            msg = json.dumps({"error": str(e)}).encode()
            self.send_response(502)
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)

    do_GET = _forward
    do_POST = _forward
    do_DELETE = _forward

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


def main():
    eps = local_endpoints()
    print("Network endpoint field:")
    for ip in eps:
        print(f"  http://{ip}:{PORT}")
    print(f"  http://127.0.0.1:{PORT}")
    print(f"Authorization key: {XAPI_KEY[:8]}...")
    print(f"Redirecting all requests -> {UPSTREAM}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()