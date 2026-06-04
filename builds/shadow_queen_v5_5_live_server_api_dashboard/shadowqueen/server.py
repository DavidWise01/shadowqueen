
import json
from pathlib import Path
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from urllib.parse import urlparse

DEFAULT_DATA={
 "status":{"version":"5.5.0","service":"shadow-queen-live-dashboard","state":"online","phase":"live"},
 "offices":[{"id":"north","status":"healthy","trust":94},{"id":"south","status":"healthy","trust":88},{"id":"east","status":"healthy","trust":91},{"id":"west","status":"degraded","trust":71}],
 "credentials":{"active":875,"revoked":75,"expired":50,"verification_success_rate":0.982},
 "fraud":{"duplicate_identity":8,"forged_credential":4,"revoked_credential_presented":11,"authority_escalation":3,"cross_office_conflict":6},
 "authority":{"active_grants":64,"revoked_grants":9,"scope_denials":14},
 "analytics":{"mesh_health":0.94,"revocation_propagation":0.91,"investigation_throughput":0.88,"trust_score":0.9}
}
class Store:
    def __init__(self,path="data/live_state.json"):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
        if not self.path.exists(): self.path.write_text(json.dumps(DEFAULT_DATA,indent=2))
    def read(self): return json.loads(self.path.read_text())
    def routes(self):
        d=self.read()
        return {"/api/status":d["status"],"/api/offices":d["offices"],"/api/credentials":d["credentials"],"/api/fraud":d["fraud"],"/api/authority":d["authority"],"/api/analytics":d["analytics"],"/api/all":d}
def handler(store,web):
    web=Path(web)
    class H(BaseHTTPRequestHandler):
        def send_json(self,o,code=200):
            b=json.dumps(o,indent=2).encode()
            self.send_response(code); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b)
        def send_file(self,p):
            if not p.exists(): self.send_json({"error":"not_found"},404); return
            b=p.read_bytes(); self.send_response(200); self.send_header("Content-Type","text/html"); self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b)
        def do_GET(self):
            p=urlparse(self.path).path; r=store.routes()
            if p in r: self.send_json(r[p]); return
            if p in ("/","/dashboard"): self.send_file(web/"index.html"); return
            self.send_json({"error":"unknown_route","routes":list(r.keys())+["/dashboard"]},404)
        def log_message(self,*args): pass
    return H
def run(host="127.0.0.1",port=8787,data="data/live_state.json",web="web"):
    srv=ThreadingHTTPServer((host,port),handler(Store(data),web))
    print(f"http://{host}:{port}/dashboard")
    srv.serve_forever()
