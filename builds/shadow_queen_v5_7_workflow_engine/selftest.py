
from pathlib import Path
import tempfile
from shadowqueen.workflow import WorkflowEngine,seed_demo
with tempfile.TemporaryDirectory() as td:
    r=seed_demo(td); st=r["stats"]
    assert st["defs"]==5
    assert st["workflows"]==5
    assert st["decisions"]>=18
    assert r["invalid"]["ok"] is False
    e=WorkflowEngine(Path(td)/"workflow.db","office:north")
    assert e.stats()["ledger"]["ok"] is True
    assert e.stats()["db_integrity"]=="ok"
    assert e.bundle(Path(td)/"workflow.zip")["exists"]
print("SELFTEST PASS")
