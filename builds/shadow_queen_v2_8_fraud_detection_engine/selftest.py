from pathlib import Path
import tempfile
from shadowqueen.core import Store, FraudEngine
from shadowqueen.cli import seed_demo
with tempfile.TemporaryDirectory() as td:
    s=Store(Path(td)/"fraud.db","north"); seed_demo(s); result=FraudEngine(s).analyze()
    assert result["findings"] >= 5, result
    scores=s.risk_scores(); assert any(r["severity"] in ("high","critical") for r in scores), scores
    assert s.audit("auditor")["result"] in ("warning","critical")
    assert s.verify_ledger()["ok"] is True
    assert s.stats()["db_integrity"]=="ok"
    assert s.bundle(Path(td)/"fraud.zip")["exists"]
print("SELFTEST PASS")
