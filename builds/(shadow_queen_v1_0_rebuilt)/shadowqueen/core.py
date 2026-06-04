
import time, json, sqlite3, hashlib
from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass(frozen=True)
class Event:
    source_id: str
    event_type: str
    timestamp: float = 0.0
    phase: str = "0"
    layer: str = "L2"
    features: Dict[str, Any] = field(default_factory=dict)

    def fingerprint(self):
        return hashlib.sha256(
            json.dumps(self.__dict__, sort_keys=True, default=str).encode()
        ).hexdigest()

class Store:
    def __init__(self, path="shadowqueen.db"):
        self.conn = sqlite3.connect(path)
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS events(ts REAL, source_id TEXT, event_type TEXT, severity TEXT)"
        )
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS heartbeats(ts REAL, status TEXT)"
        )
        self.conn.commit()

    def record(self, event, severity="info"):
        self.conn.execute(
            "INSERT INTO events VALUES(?,?,?,?)",
            (time.time(), event.source_id, event.event_type, severity),
        )
        self.conn.commit()

    def heartbeat(self, status="ok"):
        self.conn.execute(
            "INSERT INTO heartbeats VALUES(?,?)",
            (time.time(), status),
        )
        self.conn.commit()

class ShadowQueen:
    def classify(self, event):
        if event.phase == "-1":
            return {"severity": "high", "action": "quarantine"}
        if event.layer == "L5" and event.features.get("payload_read_attempt"):
            return {"severity": "critical", "action": "quarantine"}
        return {"severity": "info", "action": "allow"}
