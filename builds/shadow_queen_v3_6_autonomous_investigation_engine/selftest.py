
from pathlib import Path
import tempfile
from shadowqueen.core import InvestigationEngine,seed_demo
with tempfile.TemporaryDirectory() as td:
    e=InvestigationEngine(Path(td)/"investigations.db","test")
    seed_demo(e)
    assert e.stats()["cases"]==3
    assert e.stats()["evidence"]==3
    assert e.stats()["triage"]==3
    assert e.stats()["actions"]==3
    assert e.dashboard()["critical"]>=1
    assert e.verify_ledger()["ok"] is True
    assert e.stats()["db_integrity"]=="ok"
    assert e.bundle(Path(td)/"investigations.zip")["exists"]
print("SELFTEST PASS")
