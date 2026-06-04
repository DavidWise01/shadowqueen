
import tempfile,threading,urllib.request
from pathlib import Path
from http.server import ThreadingHTTPServer
from shadowqueen.server import Store,handler
with tempfile.TemporaryDirectory() as td:
    web=Path(td)/"web"; web.mkdir(); web.joinpath("index.html").write_text("<html>ok</html>")
    srv=ThreadingHTTPServer(("127.0.0.1",0),handler(Store(Path(td)/"live.json"),web))
    port=srv.server_address[1]
    th=threading.Thread(target=srv.serve_forever,daemon=True); th.start()
    try:
        for route in ["/api/status","/api/offices","/api/credentials","/api/fraud","/api/authority","/api/analytics","/api/all","/dashboard"]:
            r=urllib.request.urlopen(f"http://127.0.0.1:{port}{route}",timeout=5)
            assert r.status==200 and r.read()
    finally:
        srv.shutdown()
print("SELFTEST PASS")
