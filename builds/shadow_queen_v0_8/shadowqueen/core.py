
from dataclasses import dataclass, field
from typing import Dict, Any
import json, hashlib, sqlite3, time
from pathlib import Path

@dataclass(frozen=True)
class Event:
    source_id:str
    event_type:str
    timestamp:float=0.0
    phase:str="0"
    layer:str="L2"
    features:Dict[str,Any]=field(default_factory=dict)

    @classmethod
    def from_dict(cls,d):
        return cls(
            source_id=str(d["source_id"]),
            event_type=str(d["event_type"]),
            timestamp=float(d.get("timestamp",time.time())),
            phase=str(d.get("phase","0")),
            layer=str(d.get("layer","L2")),
            features=dict(d.get("features",{}))
        )

    def fingerprint(self):
        return hashlib.sha256(json.dumps(self.__dict__,sort_keys=True,default=str).encode()).hexdigest()

class Store:
    def __init__(self,path="shadowqueen.db"):
        self.conn=sqlite3.connect(Path(path)); self.conn.row_factory=sqlite3.Row
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,ts REAL,source_id TEXT,event_type TEXT,action TEXT,reason TEXT,severity TEXT,fingerprint TEXT,decision_json TEXT);
        CREATE TABLE IF NOT EXISTS alerts(id INTEGER PRIMARY KEY,ts REAL,source_id TEXT,event_type TEXT,severity TEXT,reason TEXT,recommended_action TEXT,alert_json TEXT);
        CREATE TABLE IF NOT EXISTS baselines(key TEXT PRIMARY KEY,event_type TEXT,source_id TEXT,count INTEGER,first_seen REAL,last_seen REAL);
        """); self.conn.commit()

    def learn(self,e):
        key=f"{e.event_type}:{e.source_id}"; now=time.time()
        self.conn.execute("""INSERT INTO baselines(key,event_type,source_id,count,first_seen,last_seen) VALUES(?,?,?,?,?,?)
        ON CONFLICT(key) DO UPDATE SET count=baselines.count+1,last_seen=excluded.last_seen""",(key,e.event_type,e.source_id,1,now,now))
        self.conn.commit()

    def baseline_score(self,e):
        key=f"{e.event_type}:{e.source_id}"
        row=self.conn.execute("SELECT count FROM baselines WHERE key=?",(key,)).fetchone()
        if row is None: return {"known":False,"count":0,"drift":"new_source_or_type","score":0.75}
        if row["count"]<3: return {"known":True,"count":row["count"],"drift":"low_confidence_baseline","score":0.25}
        return {"known":True,"count":row["count"],"drift":"normal","score":0.0}

    def record(self,e,d,learn=False):
        now=time.time()
        self.conn.execute("INSERT INTO events(ts,source_id,event_type,action,reason,severity,fingerprint,decision_json) VALUES(?,?,?,?,?,?,?,?)",(now,e.source_id,e.event_type,d["action"],d["reason"],d["severity"],d["fingerprint"],json.dumps(d,default=str)))
        if learn and d["action"]=="allow": self.learn(e)
        if d["severity"] in ("medium","high","critical"):
            rec={"medium":"track lineage and increase sampling","high":"quarantine source and preserve evidence","critical":"quarantine immediately and block propagation"}[d["severity"]]
            self.conn.execute("INSERT INTO alerts(ts,source_id,event_type,severity,reason,recommended_action,alert_json) VALUES(?,?,?,?,?,?,?)",(now,e.source_id,e.event_type,d["severity"],d["reason"],rec,json.dumps(d,default=str)))
        self.conn.commit()

    def stats(self):
        return {"events":self.conn.execute("SELECT COUNT(*) n FROM events").fetchone()["n"],"alerts":self.conn.execute("SELECT COUNT(*) n FROM alerts").fetchone()["n"],"baselines":self.conn.execute("SELECT COUNT(*) n FROM baselines").fetchone()["n"],"by_severity":{r["severity"]:r["n"] for r in self.conn.execute("SELECT severity,COUNT(*) n FROM events GROUP BY severity")}}
    def baselines(self,limit=50):
        return [dict(r) for r in self.conn.execute("SELECT key,event_type,source_id,count FROM baselines ORDER BY count DESC LIMIT ?",(limit,))]
    def alerts(self,limit=50):
        return [dict(r) for r in self.conn.execute("SELECT ts,source_id,event_type,severity,reason,recommended_action FROM alerts ORDER BY id DESC LIMIT ?",(limit,))]

class ShadowQueen:
    def __init__(self,store):
        self.store=store

    def classify(self,e,learn_mode=False):
        base=self.store.baseline_score(e)
        if e.phase=="-1":
            action,reason,severity="quarantine","shadow_phase","high"
        elif e.layer=="L5" and e.features.get("payload_read_attempt",False):
            action,reason,severity="quarantine","payload_read_attempt","critical"
        elif not learn_mode and base["score"]>=0.75:
            action,reason,severity="track","baseline_drift_new","medium"
        elif not learn_mode and base["score"]>=0.25:
            action,reason,severity="track","baseline_low_confidence","low"
        else:
            action,reason,severity="allow","baseline_clean","info"
        return {"source_id":e.source_id,"event_type":e.event_type,"action":action,"reason":reason,"severity":severity,"fingerprint":e.fingerprint(),"baseline":base}
