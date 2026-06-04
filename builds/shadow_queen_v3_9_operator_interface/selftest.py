
from pathlib import Path
import tempfile
from shadowqueen.core import OperatorInterface, seed_demo

with tempfile.TemporaryDirectory() as td:
    ui=OperatorInterface(Path(td)/"operator.db","operator:test")
    dash=seed_demo(ui)
    assert dash["status"] == "ready"
    assert ui.stats()["cards"] == 3
    assert ui.stats()["queues"] == 2
    assert ui.stats()["reviews"] == 1
    assert ui.verify_ledger()["ok"] is True
    assert ui.stats()["db_integrity"] == "ok"
    assert ui.bundle(Path(td)/"operator.zip")["exists"]
print("SELFTEST PASS")
