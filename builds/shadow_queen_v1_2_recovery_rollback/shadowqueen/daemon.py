
import json, time, logging
from pathlib import Path
from logging.handlers import RotatingFileHandler
from .core import Event, Store, ShadowQueen, RecoveryManager

DEFAULT_CONFIG = {
    "db": "shadowqueen.db",
    "iterations": 1,
    "interval": 0.1,
    "log_file": "shadowqueen.log",
    "recovery_dir": "recovery",
    "checkpoint_on_start": True,
    "checkpoint_on_quarantine": True,
    "events": [{"source_id":"daemon:good","event_type":"daemon_tick","phase":"good"}]
}

def load_config(path=None):
    if not path:
        return DEFAULT_CONFIG.copy()
    p = Path(path)
    if not p.exists():
        p.write_text(json.dumps(DEFAULT_CONFIG, indent=2))
        return DEFAULT_CONFIG.copy()
    cfg = DEFAULT_CONFIG.copy()
    cfg.update(json.loads(p.read_text()))
    return cfg

def run_daemon(config_path=None):
    cfg = load_config(config_path)
    logger = logging.getLogger("shadowqueen")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    h = RotatingFileHandler(cfg["log_file"], maxBytes=256000, backupCount=2)
    logger.addHandler(h)

    store = Store(cfg["db"])
    queen = ShadowQueen()
    recovery = RecoveryManager(store, cfg["recovery_dir"])

    if cfg.get("checkpoint_on_start", True):
        recovery.checkpoint("startup", config_path)

    for _ in range(int(cfg.get("iterations", 1))):
        actions = {}
        for raw in cfg.get("events", []):
            event = Event.from_dict(raw)
            decision = queen.classify(event)
            store.record_event(event, decision)
            actions[decision["action"]] = actions.get(decision["action"], 0) + 1
            if decision["action"] == "quarantine" and cfg.get("checkpoint_on_quarantine", True):
                recovery.checkpoint("quarantine", config_path)
        store.heartbeat("ok", {"actions": actions})
        logger.info("heartbeat %s", actions)
        time.sleep(float(cfg.get("interval", 0.1)))

    return store.stats()
