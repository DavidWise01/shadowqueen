
import time, json, sqlite3, hashlib, shutil, zipfile
from dataclasses import dataclass, field
from typing import Dict, Any
from pathlib import Path

@dataclass(frozen=True)
class Event:
    source_id: str
    event_type: str
    timestamp: float = 0.0
    phase: str = "good"
    features: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d):
        return cls(
            source_id=str(d["source_id"]),
            event_type=str(d["event_type"]),
            timestamp=float(d.get("timestamp", time.time())),
            phase=str(d.get("phase", "good")),
            features=dict(d.get("features", {})),
        )

    def fingerprint(self):
        return hashlib.sha256(json.dumps(self.__dict__, sort_keys=True, default=str).encode()).hexdigest()

def sha256_file(path):
    p = Path(path)
    if not p.exists():
        return None
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

class Store:
    def __init__(self, path="shadowqueen.db"):
        self.path = Path(path)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,ts REAL,source_id TEXT,event_type TEXT,phase TEXT,action TEXT,reason TEXT,severity TEXT,fingerprint TEXT);
        CREATE TABLE IF NOT EXISTS snapshots(id INTEGER PRIMARY KEY,ts REAL,label TEXT,db_backup TEXT,config_backup TEXT,db_sha256 TEXT,config_sha256 TEXT);
        CREATE TABLE IF NOT EXISTS recovery_actions(id INTEGER PRIMARY KEY,ts REAL,action TEXT,label TEXT,result TEXT,details_json TEXT);
        CREATE TABLE IF NOT EXISTS heartbeats(id INTEGER PRIMARY KEY,ts REAL,status TEXT,details_json TEXT);
        """)
        self.conn.commit()

    def record_event(self, event, decision):
        self.conn.execute(
            "INSERT INTO events(ts,source_id,event_type,phase,action,reason,severity,fingerprint) VALUES(?,?,?,?,?,?,?,?)",
            (time.time(), event.source_id, event.event_type, event.phase, decision["action"], decision["reason"], decision["severity"], event.fingerprint())
        )
        self.conn.commit()

    def heartbeat(self, status="ok", details=None):
        self.conn.execute(
            "INSERT INTO heartbeats(ts,status,details_json) VALUES(?,?,?)",
            (time.time(), status, json.dumps(details or {}, default=str))
        )
        self.conn.commit()

    def integrity(self):
        return self.conn.execute("PRAGMA integrity_check").fetchone()[0]

    def stats(self):
        return {
            "events": self.conn.execute("SELECT COUNT(*) n FROM events").fetchone()["n"],
            "snapshots": self.conn.execute("SELECT COUNT(*) n FROM snapshots").fetchone()["n"],
            "recovery_actions": self.conn.execute("SELECT COUNT(*) n FROM recovery_actions").fetchone()["n"],
            "heartbeats": self.conn.execute("SELECT COUNT(*) n FROM heartbeats").fetchone()["n"],
            "db_integrity": self.integrity(),
        }

class ShadowQueen:
    def classify(self, event):
        if event.phase == "good":
            action, reason, severity = "allow", "direct_good", "info"
        elif event.phase == "remirrored" and event.features.get("origin_phase") == "good":
            action, reason, severity = "allow", "remirror_origin_good", "info"
        elif event.phase == "bad":
            action, reason, severity = "quarantine", "direct_bad", "high"
        elif event.phase == "inversed":
            action, reason, severity = "quarantine", "inversion_detected", "high"
        else:
            action, reason, severity = "track", "unknown_phase", "medium"
        return {"action": action, "reason": reason, "severity": severity, "fingerprint": event.fingerprint()}

class RecoveryManager:
    def __init__(self, store, recovery_dir="recovery"):
        self.store = store
        self.recovery_dir = Path(recovery_dir)
        self.recovery_dir.mkdir(parents=True, exist_ok=True)

    def checkpoint(self, label="checkpoint", config_path=None):
        ts = int(time.time())
        safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in label)
        db_backup = self.recovery_dir / f"{safe}_{ts}.db.bak"
        self.store.conn.commit()
        shutil.copy2(self.store.path, db_backup)

        config_backup = None
        if config_path and Path(config_path).exists():
            config_backup = self.recovery_dir / f"{safe}_{ts}.config.bak.json"
            shutil.copy2(config_path, config_backup)

        db_hash = sha256_file(db_backup)
        config_hash = sha256_file(config_backup) if config_backup else None

        self.store.conn.execute(
            "INSERT INTO snapshots(ts,label,db_backup,config_backup,db_sha256,config_sha256) VALUES(?,?,?,?,?,?)",
            (time.time(), label, str(db_backup), str(config_backup) if config_backup else None, db_hash, config_hash)
        )
        self.store.conn.execute(
            "INSERT INTO recovery_actions(ts,action,label,result,details_json) VALUES(?,?,?,?,?)",
            (time.time(), "checkpoint", label, "ok", json.dumps({"db_backup": str(db_backup), "config_backup": str(config_backup) if config_backup else None}))
        )
        self.store.conn.commit()
        return {"label": label, "db_backup": str(db_backup), "config_backup": str(config_backup) if config_backup else None, "db_sha256": db_hash, "config_sha256": config_hash}

    def latest_snapshot(self, label=None):
        if label:
            row = self.store.conn.execute("SELECT * FROM snapshots WHERE label=? ORDER BY id DESC LIMIT 1", (label,)).fetchone()
        else:
            row = self.store.conn.execute("SELECT * FROM snapshots ORDER BY id DESC LIMIT 1").fetchone()
        return dict(row) if row else None

    def restore(self, label=None, restore_config_to=None):
        snap = self.latest_snapshot(label)
        if not snap:
            return {"restored": False, "reason": "no_snapshot"}

        db_backup = Path(snap["db_backup"])
        if not db_backup.exists():
            return {"restored": False, "reason": "missing_db_backup"}

        pre_restore = self.recovery_dir / f"pre_restore_{int(time.time())}.db.bak"
        self.store.conn.commit()
        shutil.copy2(self.store.path, pre_restore)
        self.store.conn.close()
        shutil.copy2(db_backup, self.store.path)

        self.store.conn = sqlite3.connect(self.store.path)
        self.store.conn.row_factory = sqlite3.Row

        config_restored = None
        if restore_config_to and snap.get("config_backup"):
            shutil.copy2(snap["config_backup"], restore_config_to)
            config_restored = str(restore_config_to)

        self.store.conn.execute(
            "INSERT INTO recovery_actions(ts,action,label,result,details_json) VALUES(?,?,?,?,?)",
            (time.time(), "restore", snap["label"], "ok", json.dumps({"pre_restore_backup": str(pre_restore), "config_restored": config_restored}))
        )
        self.store.conn.commit()
        return {"restored": True, "label": snap["label"], "pre_restore_backup": str(pre_restore), "config_restored": config_restored}

    def evidence_bundle(self, output_zip, label=None):
        snap = self.latest_snapshot(label)
        out = Path(output_zip)
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("manifest.json", json.dumps({"created": time.time(), "label": label, "snapshot": snap, "stats": self.store.stats()}, indent=2, default=str))
            if snap and snap.get("db_backup") and Path(snap["db_backup"]).exists():
                z.write(snap["db_backup"], arcname=Path(snap["db_backup"]).name)
            if snap and snap.get("config_backup") and Path(snap["config_backup"]).exists():
                z.write(snap["config_backup"], arcname=Path(snap["config_backup"]).name)
        self.store.conn.execute(
            "INSERT INTO recovery_actions(ts,action,label,result,details_json) VALUES(?,?,?,?,?)",
            (time.time(), "evidence_bundle", label or "", "ok", json.dumps({"output": str(out)}))
        )
        self.store.conn.commit()
        return {"bundle": str(out), "exists": out.exists()}
