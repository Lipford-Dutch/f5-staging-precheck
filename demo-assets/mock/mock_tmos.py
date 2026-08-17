"""Portable mock iControl REST server for the bigip-precheck demo.

Serves authentic fixture payloads over HTTPS (self-signed cert generated on
first run via openssl) so `bigip-precheck run` produces real GO / NO-GO
verdicts with no live BIG-IP.

Usage:  python mock_tmos.py <port> <healthy|degraded|warn>
Run three instances for the full demo:
    python mock_tmos.py 18443 healthy &
    python mock_tmos.py 18444 degraded &
    python mock_tmos.py 18445 warn &
"""
from __future__ import annotations
import json, os, ssl, subprocess, sys, tempfile
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# Import the project's own test fixtures so payloads stay authentic.
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", ".."))
sys.path.insert(0, os.path.join(_REPO, "tests", "python"))
from fixtures import icontrol as fx  # noqa: E402

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 18443
MODE = sys.argv[2] if len(sys.argv) > 2 else "healthy"

HEALTHY = {
    "/mgmt/tm/sys/version": fx.VERSION,
    "/mgmt/tm/sys/license": fx.LICENSE_OK,
    "/mgmt/tm/sys/provision": fx.PROVISION,
    "/mgmt/tm/sys/software/volume": fx.BOOT_VOLUMES,
    "/mgmt/tm/cm/failover-status": fx.FAILOVER_ACTIVE,
    "/mgmt/tm/cm/sync-status": fx.SYNC_IN_SYNC,
}
DEGRADED = dict(HEALTHY)
DEGRADED["/mgmt/tm/sys/license"] = fx.LICENSE_EXPIRED          # FAIL (critical)
DEGRADED["/mgmt/tm/cm/sync-status"] = fx.SYNC_CHANGES_PENDING  # FAIL
WARN = dict(HEALTHY)
_near = (datetime.now(timezone.utc) + timedelta(days=9)).strftime("%Y/%m/%d")
WARN["/mgmt/tm/sys/license"] = fx._stats({"licensedOn": "2025/01/15", "serviceCheckDate": _near})
WARN["/mgmt/tm/cm/failover-status"] = fx.FAILOVER_YELLOW       # HIGH-severity WARN (blocks --strict)
TABLE = {"healthy": HEALTHY, "degraded": DEGRADED, "warn": WARN}.get(MODE, HEALTHY)


def _self_signed() -> tuple[str, str]:
    d = tempfile.mkdtemp(prefix="mocktmos-")
    key, crt = os.path.join(d, "key.pem"), os.path.join(d, "cert.pem")
    subprocess.run(
        ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-keyout", key,
         "-out", crt, "-days", "3", "-nodes", "-subj", "/CN=mock-bigip"],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    return crt, key


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):  # quiet
        pass

    def _send(self, code, body):
        b = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_POST(self):
        if self.path == "/mgmt/shared/authn/login":
            self._send(200, {"token": {"token": "DEMO-TOKEN", "timeout": 1200}})
        else:
            self._send(404, {"code": 404})

    def do_GET(self):
        self._send(200, TABLE[self.path]) if self.path in TABLE else self._send(
            404, {"code": 404, "message": f"no mock for {self.path}"}
        )


def main() -> None:
    crt, key = _self_signed()
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(crt, key)
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), H)
    srv.socket = ctx.wrap_socket(srv.socket, server_side=True)
    print(f"mock TMOS [{MODE}] on https://127.0.0.1:{PORT}", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
