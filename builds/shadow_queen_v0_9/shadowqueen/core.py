
from dataclasses import dataclass, field
from typing import Dict, Any
import json, hashlib, sqlite3, time, shutil
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
        return cls(str(d["source_id"]),str(d["event_type"]),float(d.get("timestamp",time.time())),str(d.get("phase","0")),str(d.get("layer","L2")),dict(d.get("features",{})))
    def fingerprint(self):
        return hashlib.sha256(json.dumps(self.__dict__,sort_keys=True,default=str).encode()).hexdigest()

class Store:
    def __init__(self,path="shadowqueen.db"):
        self.conn=sqlite3.connect(Path(path)); self.conn.row_factory=sqlite3.Row
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,ts REAL,source_id TEXT,event_type TEXT,action TEXT,reason TEXT,severity TEXT,fingerprint TEXT);
        CREATE TABLE IF NOT EXISTS baselines(key TEXT PRIMARY KEY,event_type TEXT,source_id TEXT,count INTEGER);
        CREATE TABLE IF NOT EXISTS policy_actions(id INTEGER PRIMARY KEY,ts REAL,source_id TEXT,policy TEXT,result TEXT,details_json TEXT);
        CREATE TABLE IF NOT EXISTS denylist(source_id TEXT PRIMARY KEY,reason TEXT,created REAL);
        CREATE TABLE IF NOT EXISTS watchlist(source_id TEXT PRIMARY KEY,reason TEXT,created REAL,hits INTEGER);
        """); self.conn.commit()
    def learn(self,e):
        k=f"{e.event_type}:{e.source_id}"
        self.conn.execute("""INSERT INTO baselines(key,event_type,source_id,count) VALUES(?,?,?,1)
        ON CONFLICT(key) DO UPDATE SET count=baselines.count+1""",(k,e.event_type,e.source_id)); self.conn.commit()
    def baseline_score(self,e):
        k=f"{e.event_type}:{e.source_id}"
        r=self.conn.execute("SELECT count FROM baselines WHERE key=?",(k,)).fetchone()
        if not r: return 0.75
        return 0.0 if r["count"]>=3 else 0.25
    def is_denied(self,source_id):
        return self.conn.execute("SELECT 1 FROM denylist WHERE source_id=?",(source_id,)).fetchone() is not None
    def record_event(self,e,d,learn=False):
        self.conn.execute("INSERT INTO events(ts,source_id,event_type,action,reason,severity,fingerprint) VALUES(?,?,?,?,?,?,?)",(time.time(),e.source_id,e.event_type,d["action"],d["reason"],d["severity"],d["fingerprint"]))
        if learn and d["action"]=="allow": self.learn(e)
        self.conn.commit()
    def record_policy(self,source_id,policy,result,details):
        self.conn.execute("INSERT INTO policy_actions(ts,source_id,policy,result,details_json) VALUES(?,?,?,?,?)",(time.time(),source_id,policy,result,json.dumps(details,default=str))); self.conn.commit()
    def add_deny(self,source_id,reason):
        self.conn.execute("INSERT OR REPLACE INTO denylist(source_id,reason,created) VALUES(?,?,?)",(source_id,reason,time.time())); self.conn.commit()
    def add_watch(self,source_id,reason):
        self.conn.execute("""INSERT INTO watchlist(source_id,reason,created,hits) VALUES(?,?,?,1)
        ON CONFLICT(source_id) DO UPDATE SET hits=watchlist.hits+1,reason=excluded.reason""",(source_id,reason,time.time())); self.conn.commit()
    def stats(self):
        return {"events":self.conn.execute("SELECT COUNT(*) n FROM events").fetchone()["n"],
        "baselines":self.conn.execute("SELECT COUNT(*) n FROM baselines").fetchone()["n"],
        "policy_actions":self.conn.execute("SELECT COUNT(*) n FROM policy_actions").fetchone()["n"],
        "denylist":self.conn.execute("SELECT COUNT(*) n FROM denylist").fetchone()["n"],
        "watchlist":self.conn.execute("SELECT COUNT(*) n FROM watchlist").fetchone()["n"],
        "by_severity":{r["severity"]:r["n"] for r in self.conn.execute("SELECT severity,COUNT(*) n FROM events GROUP BY severity")}}
    def list_table(self,table,limit=50):
        if table not in {"policy_actions","denylist","watchlist"}: raise ValueError("bad table")
        return [dict(r) for r in self.conn.execute(f"SELECT * FROM {table} ORDER BY 1 DESC LIMIT ?",(limit,))]

class ShadowQueen:
    def __init__(self,store): self.store=store
    def classify(self,e,learn_mode=False):
        score=self.store.baseline_score(e)
        if self.store.is_denied(e.source_id): action,reason,severity="quarantine","denylisted_source","critical"
        elif e.phase=="-1": action,reason,severity="quarantine","shadow_phase","high"
        elif e.layer=="L5" and e.features.get("payload_read_attempt",False): action,reason,severity="quarantine","payload_read_attempt","critical"
        elif not learn_mode and score>=0.75: action,reason,severity="track","baseline_drift_new","medium"
        elif not learn_mode and score>=0.25: action,reason,severity="track","baseline_low_confidence","low"
        else: action,reason,severity="allow","baseline_clean","info"
        return {"source_id":e.source_id,"event_type":e.event_type,"action":action,"reason":reason,"severity":severity,"fingerprint":e.fingerprint(),"baseline_score":score}

class PolicyEngine:
    def __init__(self,store,quarantine_dir="quarantine"):
        self.store=store; self.quarantine_dir=Path(quarantine_dir); self.quarantine_dir.mkdir(parents=True,exist_ok=True)
    def apply(self,event,decision,mode="audit"):
        sev=decision["severity"]
        if mode=="audit":
            result={"applied":False,"mode":"audit","severity":sev}
            self.store.record_policy(event.source_id,"audit","ok",result); return result
        if sev in ("medium","low"):
            self.store.add_watch(event.source_id,decision["reason"])
            result={"applied":True,"policy":"watchlist","source_id":event.source_id}
            self.store.record_policy(event.source_id,"watchlist","ok",result); return result
        if sev=="high":
            self.store.add_watch(event.source_id,decision["reason"])
            result={"applied":True,"policy":"watchlist_high","source_id":event.source_id}
            self.store.record_policy(event.source_id,"watchlist_high","ok",result); return result
        if sev=="critical":
            self.store.add_deny(event.source_id,decision["reason"])
            copied=None; path=event.features.get("path")
            if path and Path(path).is_file():
                dst=self.quarantine_dir/(Path(path).name+".quarantine_copy")
                shutil.copy2(path,dst); copied=str(dst)
            result={"applied":True,"policy":"denylist_and_quarantine_copy","source_id":event.source_id,"copy":copied}
            self.store.record_policy(event.source_id,"denylist_and_quarantine_copy","ok",result); return result
        result={"applied":False,"policy":"none"}
        self.store.record_policy(event.source_id,"none","ok",result); return result
