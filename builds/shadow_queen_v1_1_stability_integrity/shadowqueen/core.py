
import time, json, sqlite3, hashlib
from dataclasses import dataclass, field
from typing import Dict, Any
from pathlib import Path

@dataclass(frozen=True)
class Event:
    source_id: str
    event_type: str
    timestamp: float = 0.0
    phase: str = "good"   # good / bad / inversed / remirrored
    layer: str = "L2"
    features: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d):
        return cls(
            source_id=str(d["source_id"]),
            event_type=str(d["event_type"]),
            timestamp=float(d.get("timestamp", time.time())),
            phase=str(d.get("phase", "good")),
            layer=str(d.get("layer", "L2")),
            features=dict(d.get("features", {})),
        )

    def fingerprint(self):
        return hashlib.sha256(json.dumps(self.__dict__, sort_keys=True, default=str).encode()).hexdigest()

class Integrity:
    @staticmethod
    def sha256_file(path):
        p = Path(path)
        if not p.exists():
            return None
        h = hashlib.sha256()
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def canonical_hash(obj):
        return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()

class ThreePhaseVerifier:
    """
    Stability branch:
    phase 1: classify direct event
    phase 2: classify inverse mirror
    phase 3: classify re-mirror and verify it returns to stable identity
    """
    allowed = {"good", "bad", "inversed", "remirrored"}

    def direct(self, event):
        if event.phase not in self.allowed:
            return {"state": "bad", "reason": "unknown_phase"}
        if event.phase == "good":
            return {"state": "good", "reason": "direct_good"}
        if event.phase == "bad":
            return {"state": "bad", "reason": "direct_bad"}
        if event.phase == "inversed":
            return {"state": "bad", "reason": "inversed_untrusted"}
        if event.phase == "remirrored":
            return {"state": "watch", "reason": "remirrored_requires_stability"}
        return {"state": "bad", "reason": "unreachable"}

    def inverse(self, event):
        if event.phase == "good":
            return {"state": "watch", "reason": "good_inverse_should_not_claim_authority"}
        if event.phase == "bad":
            return {"state": "bad", "reason": "bad_inverse_confirms_risk"}
        if event.phase == "inversed":
            return {"state": "bad", "reason": "inversion_detected"}
        if event.phase == "remirrored":
            return {"state": "watch", "reason": "remirror_under_observation"}
        return {"state": "bad", "reason": "inverse_unknown"}

    def remirror(self, event):
        if event.phase == "good":
            return {"state": "good", "reason": "remirror_returns_good"}
        if event.phase == "remirrored" and event.features.get("origin_phase") == "good":
            return {"state": "good", "reason": "remirror_origin_good"}
        if event.phase == "bad":
            return {"state": "bad", "reason": "remirror_still_bad"}
        if event.phase == "inversed":
            return {"state": "bad", "reason": "remirror_failed_inversion_persisted"}
        return {"state": "watch", "reason": "remirror_inconclusive"}

    def verify(self, event):
        phases = [self.direct(event), self.inverse(event), self.remirror(event)]
        states = [p["state"] for p in phases]

        # Remirrored-good is allowed when it explicitly returns to a good origin.
        # This is the stability closure: inverse was observed, then re-mirror returned.
        if event.phase == "remirrored" and event.features.get("origin_phase") == "good" and phases[2]["state"] == "good":
            verdict = "allow"
            severity = "info"
        elif "bad" in states:
            verdict = "quarantine"
            severity = "high"
        elif states.count("good") >= 2:
            verdict = "allow"
            severity = "info"
        else:
            verdict = "track"
            severity = "medium"
        return {"verdict": verdict, "severity": severity, "checks": phases}

class Store:
    def __init__(self, path="shadowqueen.db"):
        self.path = Path(path)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS events(
            id INTEGER PRIMARY KEY,
            ts REAL,
            source_id TEXT,
            event_type TEXT,
            phase TEXT,
            action TEXT,
            reason TEXT,
            severity TEXT,
            fingerprint TEXT,
            decision_json TEXT
        );
        CREATE TABLE IF NOT EXISTS integrity(
            key TEXT PRIMARY KEY,
            value TEXT,
            ts REAL
        );
        CREATE TABLE IF NOT EXISTS heartbeats(
            id INTEGER PRIMARY KEY,
            ts REAL,
            status TEXT,
            details_json TEXT
        );
        """)
        self.conn.commit()

    def record_event(self, event, decision):
        self.conn.execute(
            "INSERT INTO events(ts,source_id,event_type,phase,action,reason,severity,fingerprint,decision_json) VALUES(?,?,?,?,?,?,?,?,?)",
            (
                time.time(),
                event.source_id,
                event.event_type,
                event.phase,
                decision["action"],
                decision["reason"],
                decision["severity"],
                decision["fingerprint"],
                json.dumps(decision, default=str),
            ),
        )
        self.conn.commit()

    def set_integrity(self, key, value):
        self.conn.execute(
            "INSERT OR REPLACE INTO integrity(key,value,ts) VALUES(?,?,?)",
            (key, value, time.time()),
        )
        self.conn.commit()

    def get_integrity(self, key):
        row = self.conn.execute("SELECT value FROM integrity WHERE key=?", (key,)).fetchone()
        return row["value"] if row else None

    def heartbeat(self, status="ok", details=None):
        self.conn.execute(
            "INSERT INTO heartbeats(ts,status,details_json) VALUES(?,?,?)",
            (time.time(), status, json.dumps(details or {}, default=str)),
        )
        self.conn.commit()

    def db_integrity_check(self):
        row = self.conn.execute("PRAGMA integrity_check").fetchone()
        return row[0]

    def stats(self):
        return {
            "events": self.conn.execute("SELECT COUNT(*) n FROM events").fetchone()["n"],
            "heartbeats": self.conn.execute("SELECT COUNT(*) n FROM heartbeats").fetchone()["n"],
            "integrity_records": self.conn.execute("SELECT COUNT(*) n FROM integrity").fetchone()["n"],
            "by_severity": {
                r["severity"]: r["n"]
                for r in self.conn.execute("SELECT severity, COUNT(*) n FROM events GROUP BY severity")
            },
            "db_integrity": self.db_integrity_check(),
        }

class ShadowQueen:
    def __init__(self, store):
        self.store = store
        self.verifier = ThreePhaseVerifier()

    def classify(self, event):
        proof = self.verifier.verify(event)
        reason = proof["checks"][0]["reason"]
        if proof["verdict"] == "quarantine":
            reason = next((c["reason"] for c in proof["checks"] if c["state"] == "bad"), reason)
        return {
            "source_id": event.source_id,
            "event_type": event.event_type,
            "phase": event.phase,
            "action": proof["verdict"],
            "reason": reason,
            "severity": proof["severity"],
            "fingerprint": event.fingerprint(),
            "three_phase": proof,
        }
