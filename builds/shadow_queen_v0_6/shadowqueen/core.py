
from dataclasses import dataclass, field
from typing import Dict, Any
import json, hashlib, time, sqlite3
from pathlib import Path

@dataclass(frozen=True)
class Event:
    source_id: str
    event_type: str
    timestamp: float = 0.0
    features: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d):
        return cls(str(d["source_id"]), str(d["event_type"]), float(d.get("timestamp", time.time())), dict(d.get("features", {})))

    def fingerprint(self):
        return hashlib.sha256(json.dumps(self.__dict__, sort_keys=True, default=str).encode()).hexdigest()

class NestedClosure:
    def evaluate(self, event):
        f = event.features
        checks = {
            "left_pair_closed": list(f.get("left_pair", [1,2])) == [1,2],
            "right_pair_closed": list(f.get("right_pair", [3,4])) == [3,4],
            "doubled_null_region": int(f.get("null_count", 2)) >= 2,
            "outer_wrap_present": bool(f.get("outer_wrap", True)),
            "not_stacking": not bool(f.get("stacking", False)),
            "opaque_to_parent": not bool(f.get("internals_exposed", False)),
            "airgap_no_ack": not bool(f.get("ack_crossed_airgap", False)),
            "depth_bounded": 0 <= int(f.get("depth", 1)) <= 64,
        }
        checks["passed"] = all(checks.values())
        return checks

class Store:
    def __init__(self, path="shadowqueen.db"):
        self.conn=sqlite3.connect(Path(path)); self.conn.row_factory=sqlite3.Row
        self.conn.execute("CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,ts REAL,source_id TEXT,event_type TEXT,fingerprint TEXT,action TEXT,reason TEXT,decision_json TEXT)")
        self.conn.commit()
    def record(self,e,d):
        self.conn.execute("INSERT INTO events(ts,source_id,event_type,fingerprint,action,reason,decision_json) VALUES(?,?,?,?,?,?,?)",(time.time(),e.source_id,e.event_type,d["fingerprint"],d["action"],d["reason"],json.dumps(d,default=str)))
        self.conn.commit()
    def stats(self):
        return {"events":self.conn.execute("SELECT COUNT(*) n FROM events").fetchone()["n"],"by_action":{r["action"]:r["n"] for r in self.conn.execute("SELECT action,COUNT(*) n FROM events GROUP BY action")},"by_type":{r["event_type"]:r["n"] for r in self.conn.execute("SELECT event_type,COUNT(*) n FROM events GROUP BY event_type")}}
    def recent(self,limit=10):
        return [dict(r) for r in self.conn.execute("SELECT ts,source_id,event_type,action,reason FROM events ORDER BY id DESC LIMIT ?",(limit,))]

class ShadowQueen:
    def __init__(self):
        self.nested = NestedClosure()
    def classify(self,event):
        nested = self.nested.evaluate(event)
        if event.event_type == "nested_closure" and not nested["passed"]:
            action="quarantine"; reason=next(k for k,v in nested.items() if k!="passed" and not v)
        elif event.event_type == "nested_closure":
            action="allow"; reason="closure_opaque"
        else:
            action="allow"; reason="baseline_clean"
        return {"source_id":event.source_id,"event_type":event.event_type,"action":action,"reason":reason,"fingerprint":event.fingerprint(),"nested_closure":nested}
