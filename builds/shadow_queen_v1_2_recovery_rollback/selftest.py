
from pathlib import Path
import tempfile, json
from shadowqueen.core import Event, Store, ShadowQueen, RecoveryManager
from shadowqueen.daemon import run_daemon

with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    db = td / "sq.db"
    config = td / "config.json"
    config.write_text(json.dumps({"db": str(db), "iterations": 1, "interval": 0.01, "log_file": str(td/"sq.log"), "recovery_dir": str(td/"recovery"), "events": [{"source_id":"good","event_type":"unit","phase":"good"}]}))

    store = Store(db)
    queen = ShadowQueen()
    recovery = RecoveryManager(store, td / "recovery")

    good = Event.from_dict({"source_id":"good","event_type":"unit","phase":"good"})
    d = queen.classify(good)
    store.record_event(good, d)
    snap = recovery.checkpoint("clean", config)
    assert Path(snap["db_backup"]).exists()

    bad = Event.from_dict({"source_id":"bad","event_type":"unit","phase":"bad"})
    store.record_event(bad, queen.classify(bad))
    assert store.stats()["events"] == 2

    restored = recovery.restore("clean", td / "restored.config.json")
    assert restored["restored"] is True

    restored_store = Store(db)
    assert restored_store.stats()["events"] == 1

    bundle = RecoveryManager(restored_store, td / "recovery").evidence_bundle(td / "evidence.zip", "clean")
    assert Path(bundle["bundle"]).exists()

    stats = run_daemon(config)
    assert stats["heartbeats"] >= 1
    assert stats["db_integrity"] == "ok"

print("SELFTEST PASS")
