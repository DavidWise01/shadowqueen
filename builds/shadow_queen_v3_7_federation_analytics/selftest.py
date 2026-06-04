
from pathlib import Path
import tempfile
from shadowqueen.core import Analytics,seed_demo
with tempfile.TemporaryDirectory() as td:
    a=Analytics(Path(td)/"analytics.db","test")
    d=seed_demo(a)
    assert d["status"] in ("warning","critical")
    assert a.stats()["events"]==6
    assert a.stats()["offices"]>=3
    assert a.verify_ledger()["ok"] is True
    assert a.stats()["db_integrity"]=="ok"
    assert a.bundle(Path(td)/"analytics.zip")["exists"]
print("SELFTEST PASS")
