
from pathlib import Path
import tempfile
from shadowqueen.core import FederationOps,seed_demo
with tempfile.TemporaryDirectory() as td:
    ops=FederationOps(Path(td)/"ops.db","shadow-fed")
    dash=seed_demo(ops)
    assert dash["office_count"]==4
    assert dash["open_drift"]>=2
    assert dash["open_cases"]>=1
    ops.quarantine("west","ops","test")
    assert "west" in ops.dashboard()["quarantined"]
    ops.recover("west","ops","test")
    assert ops.verify_ledger()["ok"] is True
    assert ops.stats()["db_integrity"]=="ok"
    assert ops.bundle(Path(td)/"ops.zip")["exists"]
print("SELFTEST PASS")
