"""
server.py — Shadow Queen REST API server (stdlib only, zero dependencies)

Endpoints:
  GET  /health                   system health
  GET  /offices/{office}/stats   office statistics
  GET  /offices/{office}/credentials            list credentials
  GET  /offices/{office}/credentials/{id}       single credential
  POST /offices/{office}/credentials            issue credential
  POST /offices/{office}/credentials/{id}/transition  transition credential
  GET  /offices/{office}/ledger/verify          verify ledger integrity
  GET  /offices/{office}/threats                run threat scan
  GET  /offices/{office}/report/compliance      compliance report
  POST /offices/{office}/evidence               export evidence bundle

Authentication: Bearer token via Authorization header.
Set SHADOWQUEEN_TOKEN env var (default: 'dev-insecure-token').
"""

import json
import os
import re
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urlparse, parse_qs

from .core import Store, Replicator
from .detector import ThreatDetector
from .reports import ReportGenerator

# token — in production: rotate, use env var, prefer short-lived JWTs
_TOKEN = os.environ.get("SHADOWQUEEN_TOKEN", "dev-insecure-token")

# ─────────────────────────────────────────────────────────────────────────────
#  ROUTER
# ─────────────────────────────────────────────────────────────────────────────

ROUTES = [
    # (method, regex, handler_name)
    ("GET",  r"^/health$",                                                          "health"),
    ("GET",  r"^/offices/(?P<office>[^/]+)/stats$",                                 "stats"),
    ("GET",  r"^/offices/(?P<office>[^/]+)/credentials$",                           "list_credentials"),
    ("GET",  r"^/offices/(?P<office>[^/]+)/credentials/(?P<cid>[^/]+)$",            "get_credential"),
    ("POST", r"^/offices/(?P<office>[^/]+)/credentials$",                           "issue_credential"),
    ("POST", r"^/offices/(?P<office>[^/]+)/credentials/(?P<cid>[^/]+)/transition$", "transition_credential"),
    ("GET",  r"^/offices/(?P<office>[^/]+)/ledger/verify$",                         "verify_ledger"),
    ("GET",  r"^/offices/(?P<office>[^/]+)/threats$",                               "threat_scan"),
    ("GET",  r"^/offices/(?P<office>[^/]+)/report/compliance$",                     "compliance_report"),
    ("POST", r"^/offices/(?P<office>[^/]+)/evidence$",                              "evidence"),
]

def _store(office: str, db_dir: Path) -> Store:
    db_dir.mkdir(parents=True, exist_ok=True)
    return Store(db_dir / f"{office}.db", office)


class Handler(BaseHTTPRequestHandler):
    db_dir: Path = Path("data")
    log_requests: bool = True

    def log_message(self, fmt, *args):
        if self.log_requests:
            super().log_message(fmt, *args)

    # ── Auth ────────────────────────────────────────────────────────────────
    def _authed(self) -> bool:
        auth = self.headers.get("Authorization", "")
        return auth == f"Bearer {_TOKEN}"

    # ── Response helpers ─────────────────────────────────────────────────────
    def _send(self, code: int, body: dict):
        data = json.dumps(body, indent=2, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Shadow-Queen-Version", "2.6.0")
        self.end_headers()
        self.wfile.write(data)

    def _ok(self, body): self._send(200, body)
    def _err(self, code, msg): self._send(code, {"error": msg})

    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0: return {}
        return json.loads(self.rfile.read(length))

    # ── Routing ──────────────────────────────────────────────────────────────
    def _route(self, method):
        if not self._authed():
            self._err(401, "unauthorized — provide Bearer token in Authorization header")
            return
        path = urlparse(self.path).path
        for meth, pattern, handler_name in ROUTES:
            if meth != method: continue
            m = re.match(pattern, path)
            if m:
                try:
                    getattr(self, f"handle_{handler_name}")(**m.groupdict())
                except Exception as e:
                    self._err(500, str(e))
                return
        self._err(404, f"no route for {method} {path}")

    def do_GET(self):  self._route("GET")
    def do_POST(self): self._route("POST")

    # ── Handlers ─────────────────────────────────────────────────────────────
    def handle_health(self):
        self._ok({"status": "ok", "version": "2.6.0", "ts": time.time()})

    def handle_stats(self, office):
        self._ok(_store(office, self.db_dir).stats())

    def handle_list_credentials(self, office):
        self._ok({"credentials": _store(office, self.db_dir).credentials()})

    def handle_get_credential(self, office, cid):
        cred = _store(office, self.db_dir).credential(cid)
        if cred is None: self._err(404, f"credential {cid!r} not found")
        else: self._ok(cred)

    def handle_issue_credential(self, office):
        body = self._read_json()
        cid  = body.get("credential_id") or body.get("id")
        if not cid: self._err(400, "credential_id required"); return
        st  = _store(office, self.db_dir)
        rep = Replicator(st)
        ev  = rep.issue(
            cid,
            body.get("subject_id", ""),
            body.get("credential_type", "identity"),
            body.get("proof_hash", ""),
            body.get("targets", []),
            int(body.get("version", 1)),
        )
        self._ok({"issued": True, "event_id": ev.event_id, "credential_id": cid})

    def handle_transition_credential(self, office, cid):
        body       = self._read_json()
        event_type = body.get("event_type", "")
        valid = {"credential_suspended","credential_revoked","credential_expired","credential_replaced","credential_renewed"}
        if event_type not in valid:
            self._err(400, f"event_type must be one of {sorted(valid)}"); return
        st  = _store(office, self.db_dir)
        rep = Replicator(st)
        ev  = rep.transition(cid, event_type, body.get("targets", []), int(body.get("version", 1)))
        self._ok({"transitioned": True, "event_id": ev.event_id, "credential_id": cid, "event_type": event_type})

    def handle_verify_ledger(self, office):
        self._ok(_store(office, self.db_dir).verify_ledger())

    def handle_threat_scan(self, office):
        st = _store(office, self.db_dir)
        self._ok(ThreatDetector().scan_to_dict(st))

    def handle_compliance_report(self, office):
        st = _store(office, self.db_dir)
        self._ok(ReportGenerator(st).compliance_report())

    def handle_evidence(self, office):
        body = self._read_json()
        out  = Path(body.get("output", f"{office}_evidence_{int(time.time())}.zip"))
        result = _store(office, self.db_dir).bundle(out)
        self._ok(result)


# ─────────────────────────────────────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def serve(host="0.0.0.0", port=8400, db_dir=None, quiet=False):
    """Start the Shadow Queen HTTP API server. Blocks until KeyboardInterrupt."""
    Handler.db_dir = Path(db_dir or "data")
    Handler.log_requests = not quiet
    server = HTTPServer((host, port), Handler)
    print(f"Shadow Queen v2.6.0 API  →  http://{host}:{port}")
    print(f"  Auth: Bearer {_TOKEN}")
    print(f"  DB dir: {Handler.db_dir.resolve()}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutdown.")
    finally:
        server.server_close()
