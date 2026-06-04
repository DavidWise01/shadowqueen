
from pathlib import Path
import tempfile
from shadowqueen.notifications import Notifications,seed_demo
with tempfile.TemporaryDirectory() as td:
    r=seed_demo(td)
    assert r["stats"]["channels"]==4
    assert r["stats"]["subscriptions"]==4
    assert r["stats"]["events"]==2
    assert r["stats"]["delivered"]==3
    assert r["stats"]["failed"]==1
    assert len(r["outbox_files"])==3
    n=Notifications(Path(td)/"notifications.db","office:north",Path(td)/"outbox")
    assert n.stats()["ledger"]["ok"] is True
    assert n.stats()["db_integrity"]=="ok"
    assert n.bundle(Path(td)/"notifications.zip")["exists"]
print("SELFTEST PASS")
