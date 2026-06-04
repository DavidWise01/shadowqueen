
from pathlib import Path
import tempfile
from shadowqueen.core import Wallet,seed_demo
with tempfile.TemporaryDirectory() as td:
    w=Wallet(Path(td)/"wallet.db","citizen:root")
    result=seed_demo(w)
    assert result["ready"]["status"]=="ready"
    assert result["blocked"]["status"]=="blocked"
    assert w.stats()["credentials"]==3
    assert w.stats()["proofs"]==2
    assert w.verify_ledger()["ok"] is True
    assert w.stats()["db_integrity"]=="ok"
    assert w.bundle(Path(td)/"wallet.zip")["exists"]
print("SELFTEST PASS")
