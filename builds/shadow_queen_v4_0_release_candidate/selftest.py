
from pathlib import Path
import tempfile
from shadowqueen.core import RC
with tempfile.TemporaryDirectory() as td:
    rc=RC(Path(td)/"rc.db","test-rc")
    result=rc.run_all()
    assert result["status"]=="release_candidate_ready", result
    st=rc.stats()
    assert st["modules"]==12
    assert st["tests"]==3
    assert st["chaos"]==5
    assert st["recovery"]==4
    assert st["governance"]==5
    assert st["matrices"]==5
    assert st["ledger"]["ok"] is True
    assert st["db_integrity"]=="ok"
    assert rc.bundle(Path(td)/"rc.zip")["exists"]
print("SELFTEST PASS")
