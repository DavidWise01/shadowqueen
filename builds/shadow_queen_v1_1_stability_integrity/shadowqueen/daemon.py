
import json, time, logging
from pathlib import Path
from logging.handlers import RotatingFileHandler
from .core import Event, Store, ShadowQueen, Integrity

DEFAULT_CONFIG = {
    "db": "shadowqueen.db",
    "iterations": 1,
    "interval": 0.1,
    "log_file": "shadowqueen.log",
    "events": [
        {"source_id": "daemon:good", "event_type": "daemon_tick", "phase": "good"}
    ]
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

def setup_logger(path):
    logger = logging.getLogger("shadowqueen")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    handler = RotatingFileHandler(path, maxBytes=256000, backupCount=2)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    return logger

def run_daemon(config_path=None):
    cfg = load_config(config_path)
    logger = setup_logger(cfg["log_file"])
    store = Store(cfg["db"])
    queen = ShadowQueen(store)

    config_hash = Integrity.sha256_file(config_path) if config_path else Integrity.canonical_hash(cfg)
    previous_hash = store.get_integrity("config_sha256")
    tamper = previous_hash is not None and previous_hash != config_hash
    store.set_integrity("config_sha256", config_hash)

    iterations = int(cfg.get("iterations", 1))
    interval = float(cfg.get("interval", 0.1))
    logger.info("daemon starting tamper=%s", tamper)

    for i in range(iterations):
        actions = {}
        for raw in cfg.get("events", []):
            event = Event.from_dict(raw)
            decision = queen.classify(event)
            store.record_event(event, decision)
            actions[decision["action"]] = actions.get(decision["action"], 0) + 1
        store.heartbeat("tamper" if tamper else "ok", {"actions": actions, "config_sha256": config_hash})
        logger.info("heartbeat actions=%s tamper=%s", actions, tamper)
        time.sleep(interval)

    return store.stats()
