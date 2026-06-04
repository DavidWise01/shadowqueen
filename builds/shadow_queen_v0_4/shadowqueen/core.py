
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from decimal import Decimal
import json, hashlib, sqlite3, time
from pathlib import Path
BASELINE=Decimal("0.00000000"); EPSILON=Decimal("0.00000001")

@dataclass(frozen=True)
class Event:
    source_id:str; event_type:str; timestamp:float=0.0; phase:str="0"; layer:str="L2"; parent_id:Optional[str]=None
    witness_index:int=257; witness_internal:bool=False; carrier:str="3-2-1-0"; rest_taken:bool=True
    silence_depth:Optional[int]=1; wiggle_sequence:str="-++-"; voltage_debt_mv:int=0; features:Dict[str,Any]=field(default_factory=dict)
    @classmethod
    def from_dict(cls,d):
        return cls(str(d["source_id"]),str(d["event_type"]),float(d.get("timestamp",time.time())),str(d.get("phase","0")),str(d.get("layer","L2")),d.get("parent_id"),int(d.get("witness_index",257)),bool(d.get("witness_internal",False)),str(d.get("carrier","3-2-1-0")),bool(d.get("rest_taken",True)),d.get("silence_depth",1),str(d.get("wiggle_sequence","-++-")),int(d.get("voltage_debt_mv",0)),dict(d.get("features",{})))
    def canonical(self):
        return self.__dict__
    def fingerprint(self):
        return hashlib.sha256(json.dumps(self.canonical(),sort_keys=True,default=str).encode()).hexdigest()

class Store:
    def __init__(self,path="shadowqueen.db"):
        self.conn=sqlite3.connect(Path(path)); self.conn.row_factory=sqlite3.Row
        self.conn.executescript("""CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,ts REAL,source_id TEXT,event_type TEXT,fingerprint TEXT,action TEXT,reason TEXT,delta TEXT,event_json TEXT,decision_json TEXT);
CREATE TABLE IF NOT EXISTS memory(fingerprint TEXT PRIMARY KEY,action TEXT,first_seen REAL,last_seen REAL,hits INTEGER);
CREATE TABLE IF NOT EXISTS lineage(source_id TEXT PRIMARY KEY,parent_id TEXT,risk TEXT,first_seen REAL,last_seen REAL);"""); self.conn.commit()
    def load_memory(self): return {r["fingerprint"]:r["action"] for r in self.conn.execute("SELECT fingerprint,action FROM memory")}
    def load_risk(self): return {r["source_id"]:r["risk"] for r in self.conn.execute("SELECT source_id,risk FROM lineage WHERE risk IS NOT NULL")}
    def record(self,e,d):
        now=time.time()
        self.conn.execute("INSERT INTO events(ts,source_id,event_type,fingerprint,action,reason,delta,event_json,decision_json) VALUES(?,?,?,?,?,?,?,?,?)",(now,e.source_id,e.event_type,d["fingerprint"],d["action"],d["reason"],d["delta"],json.dumps(e.canonical(),default=str),json.dumps(d,default=str)))
        if d["action"]!="allow":
            self.conn.execute("""INSERT INTO memory(fingerprint,action,first_seen,last_seen,hits) VALUES(?,?,?,?,1)
ON CONFLICT(fingerprint) DO UPDATE SET action=excluded.action,last_seen=excluded.last_seen,hits=memory.hits+1""",(d["fingerprint"],d["action"],now,now))
        self.conn.execute("""INSERT INTO lineage(source_id,parent_id,risk,first_seen,last_seen) VALUES(?,?,?,?,?)
ON CONFLICT(source_id) DO UPDATE SET parent_id=COALESCE(excluded.parent_id,lineage.parent_id),risk=COALESCE(excluded.risk,lineage.risk),last_seen=excluded.last_seen""",(e.source_id,e.parent_id,d["action"] if d["action"]!="allow" else None,now,now)); self.conn.commit()
    def stats(self):
        return {"events":self.conn.execute("SELECT COUNT(*) n FROM events").fetchone()["n"],"by_action":{r["action"]:r["n"] for r in self.conn.execute("SELECT action,COUNT(*) n FROM events GROUP BY action")},"by_type":{r["event_type"]:r["n"] for r in self.conn.execute("SELECT event_type,COUNT(*) n FROM events GROUP BY event_type")},"fingerprint_memory":self.conn.execute("SELECT COUNT(*) n FROM memory").fetchone()["n"],"lineage_nodes":self.conn.execute("SELECT COUNT(*) n FROM lineage").fetchone()["n"]}
    def recent(self,limit=10): return [dict(r) for r in self.conn.execute("SELECT ts,source_id,event_type,action,reason,delta FROM events ORDER BY id DESC LIMIT ?",(limit,))]

class ShadowQueen:
    def __init__(self,memory=None,risk=None): self.memory=dict(memory or {}); self.risk=dict(risk or {})
    def deviation(self,e):
        d=BASELINE
        if e.phase=="-1": d-=EPSILON
        if e.wiggle_sequence!="-++-" or e.carrier!="3-2-1-0" or not e.rest_taken or e.silence_depth is None: d+=EPSILON
        if e.witness_index!=257 or e.witness_internal: d+=EPSILON
        if e.voltage_debt_mv<=-422: d+=Decimal("0.00000005")
        if e.layer=="L5" and e.features.get("payload_read_attempt",False): d+=Decimal("0.00000007")
        if e.event_type=="file_change" and e.features.get("extension") in [".exe",".dll",".so",".sh",".py"]: d+=Decimal("0.00000002")
        if e.event_type=="network_connection" and e.features.get("remote_port") in [4444,1337,31337]: d+=Decimal("0.00000003")
        return d
    def gates(self,e):
        return {"witness_257":e.witness_index==257 and not e.witness_internal,"timing_rest":e.carrier=="3-2-1-0" and e.rest_taken and e.silence_depth is not None,"silicon_wiggle":e.wiggle_sequence=="-++-" and e.voltage_debt_mv>-422,"osi_content_blind":not(e.layer=="L5" and e.features.get("payload_read_attempt",False))}
    def classify(self,e):
        fp=e.fingerprint(); gs=self.gates(e); delta=self.deviation(e); pr=self.risk.get(e.parent_id) if e.parent_id else None
        if fp in self.memory: action,reason=self.memory[fp],"persistent_fingerprint_memory_hit"
        elif e.source_id in self.risk: action,reason="track","persistent_lineage_risk"
        elif pr: action,reason="track","parent_lineage_risk:"+pr
        elif not all(gs.values()): action,reason="quarantine",next(k for k,v in gs.items() if not v)
        elif abs(delta)==BASELINE: action,reason="allow","baseline_clean"
        elif delta<0 or e.phase=="-1": action,reason="quarantine","shadow_or_negative_deviation"
        elif delta>=Decimal("0.00000004"): action,reason="quarantine","high_deviation_detected"
        else: action,reason="track","first_deviation_detected"
        if action!="allow": self.memory[fp]=action; self.risk[e.source_id]=action
        return {"source_id":e.source_id,"event_type":e.event_type,"action":action,"reason":reason,"delta":str(delta),"fingerprint":fp,"gates":gs}
