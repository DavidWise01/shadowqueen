
from pathlib import Path
import tempfile
from shadowqueen.reporting import Reporting,seed_demo
with tempfile.TemporaryDirectory() as td:
    r=seed_demo(td)
    st=r["stats"]
    assert st["reports"]==6
    assert st["evidence"]>=4
    assert st["packets"]==1
    assert r["packet"]["reports"]==6
    assert r["packet"]["evidence"]>=4
    e=Reporting(Path(td)/"reports.db","office:north",Path(td)/"reports")
    assert e.stats()["ledger"]["ok"] is True
    assert e.stats()["db_integrity"]=="ok"
    assert e.bundle(Path(td)/"reporting.zip")["exists"]
print("SELFTEST PASS")
