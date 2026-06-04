
from pathlib import Path
import tempfile, json
from shadowqueen.core import Event, Store, ShadowQueen
from shadowqueen.daemon import run_daemon

with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    db = td / "sq.db"
    store = Store(db)
    queen = ShadowQueen(store)

    cases = [
        ("good", "allow"),
        ("bad", "quarantine"),
        ("inversed", "quarantine"),
        ("remirrored", "allow"),
    ]

    for phase, expected in cases:
        event = Event.from_dict({
            "source_id": f"case:{phase}",
            "event_type": "unit",
            "phase": phase,
            "features": {"origin_phase": "good"}
        })
        decision = queen.classify(event)
        store.record_event(event, decision)
        assert decision["action"] == expected, (phase, decision)

    assert store.db_integrity_check() == "ok"

    cfg = {
        "db": str(db),
        "iterations": 1,
        "interval": 0.01,
        "log_file": str(td / "sq.log"),
        "events": [{"source_id":"daemon:good","event_type":"daemon_tick","phase":"good"}]
    }
    cfgp = td / "config.json"
    cfgp.write_text(json.dumps(cfg))
    stats = run_daemon(cfgp)
    assert stats["heartbeats"] >= 1
    assert stats["db_integrity"] == "ok"
    assert (td / "sq.log").exists()

print("SELFTEST PASS")
