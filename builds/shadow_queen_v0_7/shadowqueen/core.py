
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
    def from_dict(cls,d):
        return cls(str(d["source_id"]),str(d["event_type"]),float(d.get("timestamp",time.time())),str(d.get("phase","0")),str(d.get("layer","L2")),dict(d.get("features",{})))
    def fingerprint(self):
        return hashlib.sha256(json.dumps(self.__dict__,sort_keys=True,default=str).encode()).hexdigest()

class AlertEngine:
    severity = {
        "baseline_clean":"info","closure_opaque":"info","five_body_contained":"info",
        "shadow_phase":"high","payload_read_attempt":"critical","payload_blind":"critical",
        "airgap_no_ack":"high","opaque_to_parent":"high","not_stacking":"medium",
        "outer_wrap_present":"medium","doubled_null_region":"medium",
        "gap_not_crossed":"high","observer_separated":"high","chaos_contained":"high"
    }
    actions = {
        "info":"log",
        "medium":"track lineage and increase sampling",
        "high":"quarantine source and preserve evidence",
        "critical":"quarantine immediately and block propagation"
    }
    def alert_for(self,event,decision):
        sev=self.severity.get(decision["reason"], "high" if decision["action"]=="quarantine" else "medium" if decision["action"]=="track" else "info")
        return {"source_id":event.source_id,"event_type":event.event_type,"severity":sev,"action":decision["action"],"reason":decision["reason"],"recommended_action":self.actions[sev],"fingerprint":decision["fingerprint"]}

class Store:
    def __init__(self,path="shadowqueen.db"):
        self.conn=sqlite3.connect(Path(path)); self.conn.row_factory=sqlite3.Row
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,ts REAL,source_id TEXT,event_type TEXT,fingerprint TEXT,action TEXT,reason TEXT,decision_json TEXT);
        CREATE TABLE IF NOT EXISTS alerts(id INTEGER PRIMARY KEY,ts REAL,source_id TEXT,event_type TEXT,severity TEXT,action TEXT,reason TEXT,recommended_action TEXT,fingerprint TEXT,alert_json TEXT);
        """); self.conn.commit()
    def record(self,event,decision,alert):
        now=time.time()
        self.conn.execute("INSERT INTO events(ts,source_id,event_type,fingerprint,action,reason,decision_json) VALUES(?,?,?,?,?,?,?)",(now,event.source_id,event.event_type,decision["fingerprint"],decision["action"],decision["reason"],json.dumps(decision,default=str)))
        if alert["severity"]!="info":
            self.conn.execute("INSERT INTO alerts(ts,source_id,event_type,severity,action,reason,recommended_action,fingerprint,alert_json) VALUES(?,?,?,?,?,?,?,?,?)",(now,alert["source_id"],alert["event_type"],alert["severity"],alert["action"],alert["reason"],alert["recommended_action"],alert["fingerprint"],json.dumps(alert,default=str)))
        self.conn.commit()
    def stats(self):
        return {"events":self.conn.execute("SELECT COUNT(*) n FROM events").fetchone()["n"],"alerts":self.conn.execute("SELECT COUNT(*) n FROM alerts").fetchone()["n"],"by_action":{r["action"]:r["n"] for r in self.conn.execute("SELECT action,COUNT(*) n FROM events GROUP BY action")},"by_severity":{r["severity"]:r["n"] for r in self.conn.execute("SELECT severity,COUNT(*) n FROM alerts GROUP BY severity")}}
    def alerts(self,limit=50,severity=None):
        if severity:
            rows=self.conn.execute("SELECT ts,source_id,event_type,severity,action,reason,recommended_action FROM alerts WHERE severity=? ORDER BY id DESC LIMIT ?",(severity,limit))
        else:
            rows=self.conn.execute("SELECT ts,source_id,event_type,severity,action,reason,recommended_action FROM alerts ORDER BY id DESC LIMIT ?",(limit,))
        return [dict(r) for r in rows]
    def export_report(self,path):
        data={"stats":self.stats(),"alerts":self.alerts(1000)}
        Path(path).write_text(json.dumps(data,indent=2,sort_keys=True))
        return data

class ShadowQueen:
    def __init__(self):
        self.alerts=AlertEngine()
    def nested_reason(self,f):
        if int(f.get("null_count",2))<2: return "doubled_null_region"
        if not bool(f.get("outer_wrap",True)): return "outer_wrap_present"
        if bool(f.get("stacking",False)): return "not_stacking"
        if bool(f.get("internals_exposed",False)): return "opaque_to_parent"
        if bool(f.get("ack_crossed_airgap",False)): return "airgap_no_ack"
        return None
    def five_reason(self,f):
        if bool(f.get("payload_read_attempt",False)): return "payload_blind"
        if bool(f.get("gap_crossed",False)): return "gap_not_crossed"
        if bool(f.get("observer_entangled",False)): return "observer_separated"
        if bool(f.get("inner_escape",False)): return "chaos_contained"
        return None
    def classify(self,event):
        reason=None
        if event.event_type=="nested_closure":
            reason=self.nested_reason(event.features)
            action="quarantine" if reason else "allow"
            reason=reason or "closure_opaque"
        elif event.event_type=="five_body":
            reason=self.five_reason(event.features)
            action="quarantine" if reason else "allow"
            reason=reason or "five_body_contained"
        elif event.phase=="-1":
            action="quarantine"; reason="shadow_phase"
        elif event.layer=="L5" and event.features.get("payload_read_attempt",False):
            action="quarantine"; reason="payload_read_attempt"
        else:
            action="allow"; reason="baseline_clean"
        return {"source_id":event.source_id,"event_type":event.event_type,"action":action,"reason":reason,"fingerprint":event.fingerprint()}
