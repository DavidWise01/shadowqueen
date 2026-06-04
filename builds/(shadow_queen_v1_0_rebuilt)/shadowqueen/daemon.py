
import json, time
from pathlib import Path
from .core import Event, Store, ShadowQueen

DEFAULT_CONFIG = {
    "db": "shadowqueen.db",
    "iterations": 1,
    "interval": 0.1
}

def run_daemon(config_path=None):
    cfg = DEFAULT_CONFIG.copy()

    if config_path and Path(config_path).exists():
        cfg.update(json.loads(Path(config_path).read_text()))

    store = Store(cfg["db"])
    queen = ShadowQueen()

    for i in range(cfg["iterations"]):
        event = Event(source_id=f"heartbeat:{i}", event_type="daemon_tick")
        result = queen.classify(event)
        store.record(event, result["severity"])
        store.heartbeat("ok")
        time.sleep(cfg["interval"])

    return {"status": "ok"}
