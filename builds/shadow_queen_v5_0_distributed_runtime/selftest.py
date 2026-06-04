
from pathlib import Path
import tempfile
from shadowqueen.runtime import Node,demo
with tempfile.TemporaryDirectory() as td:
    r=demo(td)
    assert r["north"]["peers"]==3
    assert r["south"]["inbox"]>=2
    assert r["east"]["inbox"]>=2
    assert r["heartbeat"]["status"]=="delivered"
    assert r["replication"]["status"]=="delivered"
    n=Node(Path(td)/"north.db","office:north","MN")
    assert n.status()["db_integrity"]=="ok"
    assert n.status()["ledger"]["ok"] is True
    assert n.bundle(Path(td)/"runtime.zip")["exists"]
print("SELFTEST PASS")
