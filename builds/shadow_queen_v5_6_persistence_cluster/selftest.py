
from pathlib import Path
import tempfile
from shadowqueen.persistence import Node,seed_demo
with tempfile.TemporaryDirectory() as td:
    r=seed_demo(td)
    assert r["north"]["items"]==20
    assert r["south"]["items"]==20
    assert r["east"]["items"]==20
    assert r["west"]["items"]==20
    assert r["syncs"][0]["status"]=="ok"
    assert r["recovery"]["recovered"] is True
    n=Node(Path(td)/"north.db","office:north")
    assert n.stats()["ledger"]["ok"]
    assert n.stats()["db_integrity"]=="ok"
    assert n.bundle(Path(td)/"cluster.zip")["exists"]
print("SELFTEST PASS")
