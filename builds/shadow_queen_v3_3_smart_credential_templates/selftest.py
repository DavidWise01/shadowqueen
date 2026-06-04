
from pathlib import Path
import tempfile
from shadowqueen.core import Templates,seed_demo
with tempfile.TemporaryDirectory() as td:
    e=Templates(Path(td)/"templates.db","north")
    r=seed_demo(e)
    assert r["good"]["ok"] is True
    assert r["bad"]["ok"] is False
    assert e.stats()["templates"]==2
    assert e.stats()["validations"]==2
    assert e.verify_ledger()["ok"] is True
    assert e.stats()["db_integrity"]=="ok"
    assert e.bundle(Path(td)/"templates.zip")["exists"]
print("SELFTEST PASS")
