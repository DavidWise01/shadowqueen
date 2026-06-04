import json
from pathlib import Path
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from urllib.parse import urlparse
class H(BaseHTTPRequestHandler):
    def j(self,o,code=200):
        b=json.dumps(o,indent=2).encode(); self.send_response(code); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        data=json.loads(Path("data/dashboard.json").read_text()); p=urlparse(self.path).path
        if p in ("/","/dashboard"):
            b=Path("web/index.html").read_bytes(); self.send_response(200); self.send_header("Content-Type","text/html"); self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b); return
        routes={"/api/status":{"version":data["version"],"status":data["status"]},"/api/federation":data["federation"],"/api/activity":data["activity"],"/api/credentials":data["credentials"],"/api/authority":data["authority"],"/api/fraud":data["fraud"],"/api/mesh":data["mesh"],"/api/reports":data["reports"],"/api/analytics":data["analytics"],"/api/all":data}
        self.j(routes[p] if p in routes else {"error":"not_found","routes":list(routes)+["/dashboard"]},200 if p in routes else 404)
    def log_message(self,*a): pass
def main():
    host,port="127.0.0.1",9090
    print(f"Shadow Queen v9.0 Final dashboard: http://{host}:{port}/dashboard")
    ThreadingHTTPServer((host,port),H).serve_forever()
if __name__=="__main__": main()
