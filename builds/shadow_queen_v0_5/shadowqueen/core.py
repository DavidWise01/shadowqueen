
from dataclasses import dataclass, field
from typing import Dict, Any
import json, hashlib, sqlite3, time
from pathlib import Path

@dataclass(frozen=True)
class Event:
    source_id: str
    event_type: str
    timestamp: float = 0.0
    phase: str = "0"
    layer: str = "L2"
    features: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d):
        return cls(
            source_id=str(d["source_id"]),
            event_type=str(d["event_type"]),
            timestamp=float(d.get("timestamp", time.time())),
            phase=str(d.get("phase", "0")),
            layer=str(d.get("layer", "L2")),
            features=dict(d.get("features", {})),
        )

    def fingerprint(self):
        return hashlib.sha256(json.dumps(self.__dict__, sort_keys=True, default=str).encode()).hexdigest()

class FiveBodyTopology:
    INNER = {"SELF", "RING", "EXT"}
    OUTER = {"+8_CARRIER", "-8_SHADOW"}

    def evaluate(self, event):
        f = event.features
        inner = f.get("inner_body")
        outer = f.get("outer_observer")
        checks = {
            "inner_valid": inner in self.INNER or inner is None,
            "outer_valid": outer in self.OUTER or outer is None,
            "gap_not_crossed": not f.get("gap_crossed", False),
            "mutual_watch": bool(f.get("mutual_observer_check", True)),
            "chaos_contained": not f.get("inner_escape", False),
            "observer_separated": not f.get("observer_entangled", False),
            "payload_blind": not f.get("payload_read_attempt", False),
        }
        checks["passed"] = all(checks.values())
        return checks

class Store:
    def __init__(self, path="shadowqueen.db"):
        self.conn = sqlite3.connect(Path(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS events(
            id INTEGER PRIMARY KEY,
            ts REAL,
            source_id TEXT,
            event_type TEXT,
            fingerprint TEXT,
            action TEXT,
            reason TEXT,
            decision_json TEXT
        );
        """)
        self.conn.commit()

    def record(self, event, decision):
        self.conn.execute(
            "INSERT INTO events(ts,source_id,event_type,fingerprint,action,reason,decision_json) VALUES(?,?,?,?,?,?,?)",
            (time.time(), event.source_id, event.event_type, decision["fingerprint"], decision["action"], decision["reason"], json.dumps(decision, default=str))
        )
        self.conn.commit()

    def stats(self):
        return {
            "events": self.conn.execute("SELECT COUNT(*) n FROM events").fetchone()["n"],
            "by_action": {r["action"]: r["n"] for r in self.conn.execute("SELECT action, COUNT(*) n FROM events GROUP BY action")},
            "by_type": {r["event_type"]: r["n"] for r in self.conn.execute("SELECT event_type, COUNT(*) n FROM events GROUP BY event_type")},
        }

    def recent(self, limit=10):
        return [dict(r) for r in self.conn.execute("SELECT ts,source_id,event_type,action,reason FROM events ORDER BY id DESC LIMIT ?", (limit,))]

class ShadowQueen:
    def __init__(self):
        self.five_body = FiveBodyTopology()

    def classify(self, event):
        five = self.five_body.evaluate(event)
        if event.event_type == "five_body" and not five["passed"]:
            action = "quarantine"
            reason = next(k for k, v in five.items() if k != "passed" and not v)
        elif event.event_type == "five_body":
            action = "allow"
            reason = "five_body_contained"
        elif event.phase == "-1":
            action = "quarantine"
            reason = "shadow_phase"
        else:
            action = "allow"
            reason = "baseline_clean"
        return {
            "source_id": event.source_id,
            "event_type": event.event_type,
            "action": action,
            "reason": reason,
            "fingerprint": event.fingerprint(),
            "five_body": five,
        }
