
from pathlib import Path
import tempfile
from shadowqueen.core import DMV, seed_demo

with tempfile.TemporaryDirectory() as td:
    d=DMV(Path(td)/"beta.db","north")
    result=seed_demo(d)
    assert result["issued"]["ok"] is True
    assert result["denied"]["ok"] is False
    assert d.stats()["citizens"]==2
    assert d.stats()["credentials"]==1
    assert d.stats()["investigations"]>=1
    assert d.verify_ledger()["ok"] is True
    assert d.stats()["db_integrity"]=="ok"
    assert d.bundle(Path(td)/"beta.zip")["exists"]
print("SELFTEST PASS")
