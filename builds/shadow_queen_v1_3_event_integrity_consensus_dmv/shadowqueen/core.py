
from dataclasses import dataclass
from collections import Counter, defaultdict
import json, hashlib, sqlite3, time
from pathlib import Path

@dataclass(frozen=True)
class IdentityRecord:
    person_id:str
    legal_name:str
    address:str
    dob:str=""
    document_id:str=""
    status:str="active"
    @classmethod
    def from_dict(cls,d):
        return cls(str(d["person_id"]),str(d.get("legal_name","")),str(d.get("address","")),str(d.get("dob","")),str(d.get("document_id","")),str(d.get("status","active")))
    def canonical(self):
        return {"person_id":self.person_id,"legal_name":self.legal_name.strip().lower(),"address":self.address.strip().lower(),"dob":self.dob,"document_id":self.document_id,"status":self.status}
    def fingerprint(self):
        return hashlib.sha256(json.dumps(self.canonical(),sort_keys=True).encode()).hexdigest()

@dataclass(frozen=True)
class ObserverEvent:
    observer_id:str
    role:str
    record:IdentityRecord
    confidence:float=1.0
    @classmethod
    def from_dict(cls,d):
        return cls(str(d["observer_id"]),str(d.get("role","clerk")),IdentityRecord.from_dict(d["record"]),float(d.get("confidence",1.0)))
    def event_hash(self):
        blob={"observer_id":self.observer_id,"role":self.role,"record_fp":self.record.fingerprint(),"confidence":round(self.confidence,4)}
        return hashlib.sha256(json.dumps(blob,sort_keys=True).encode()).hexdigest()

class VirtualDMVConsensus:
    def __init__(self,quorum=3): self.quorum=quorum
    def evaluate(self,events):
        grouped=defaultdict(list)
        for ev in events: grouped[ev.record.person_id].append(ev)
        decisions=[]
        for person_id, evs in grouped.items():
            votes=Counter(ev.record.fingerprint() for ev in evs)
            top_fp, top_count=votes.most_common(1)[0]
            dissent=[ev for ev in evs if ev.record.fingerprint()!=top_fp]
            dup=len({ev.observer_id for ev in evs})!=len(evs)
            sample=next(ev.record for ev in evs if ev.record.fingerprint()==top_fp)
            if dup:
                action,reason,severity="quarantine","duplicate_observer_vote","high"
            elif top_count>=self.quorum and not dissent:
                action,reason,severity="issue_identity","quorum_clean","info"
            elif top_count>=self.quorum and dissent:
                action,reason,severity="track","quorum_with_dissent","medium"
            elif dissent:
                action,reason,severity="quarantine","identity_disagreement_no_quorum","high"
            else:
                action,reason,severity="track","insufficient_quorum","medium"
            decisions.append({"person_id":person_id,"action":action,"reason":reason,"severity":severity,"winning_fingerprint":top_fp,"observer_count":len(evs),"winning_votes":top_count,"quorum":self.quorum,"votes":dict(votes),"dissenters":[{"observer_id":ev.observer_id,"fingerprint":ev.record.fingerprint()} for ev in dissent],"identity":sample.canonical()})
        return decisions

class Store:
    def __init__(self,path="shadowqueen_dmv.db"):
        self.conn=sqlite3.connect(Path(path)); self.conn.row_factory=sqlite3.Row
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS observer_events(id INTEGER PRIMARY KEY,ts REAL,observer_id TEXT,role TEXT,person_id TEXT,record_fingerprint TEXT,event_hash TEXT,event_json TEXT);
        CREATE TABLE IF NOT EXISTS identity_registry(person_id TEXT PRIMARY KEY,legal_name TEXT,address TEXT,dob TEXT,document_id TEXT,status TEXT,fingerprint TEXT,issued_ts REAL);
        CREATE TABLE IF NOT EXISTS consensus_decisions(id INTEGER PRIMARY KEY,ts REAL,person_id TEXT,action TEXT,reason TEXT,severity TEXT,decision_json TEXT);
        CREATE TABLE IF NOT EXISTS duplicate_events(event_hash TEXT PRIMARY KEY,first_seen REAL,hits INTEGER);
        CREATE TABLE IF NOT EXISTS heartbeats(id INTEGER PRIMARY KEY,ts REAL,status TEXT,details_json TEXT);
        """); self.conn.commit()
    def record_observer_event(self,ev):
        eh=ev.event_hash(); now=time.time()
        self.conn.execute("""INSERT INTO duplicate_events(event_hash,first_seen,hits) VALUES(?,?,1)
        ON CONFLICT(event_hash) DO UPDATE SET hits=duplicate_events.hits+1""",(eh,now))
        self.conn.execute("INSERT INTO observer_events(ts,observer_id,role,person_id,record_fingerprint,event_hash,event_json) VALUES(?,?,?,?,?,?,?)",(now,ev.observer_id,ev.role,ev.record.person_id,ev.record.fingerprint(),eh,json.dumps({"observer_id":ev.observer_id,"role":ev.role,"record":ev.record.canonical(),"confidence":ev.confidence})))
        self.conn.commit()
    def record_decision(self,d):
        self.conn.execute("INSERT INTO consensus_decisions(ts,person_id,action,reason,severity,decision_json) VALUES(?,?,?,?,?,?)",(time.time(),d["person_id"],d["action"],d["reason"],d["severity"],json.dumps(d)))
        if d["action"]=="issue_identity":
            ident=d["identity"]
            self.conn.execute("INSERT OR REPLACE INTO identity_registry(person_id,legal_name,address,dob,document_id,status,fingerprint,issued_ts) VALUES(?,?,?,?,?,?,?,?)",(ident["person_id"],ident["legal_name"],ident["address"],ident["dob"],ident["document_id"],ident["status"],d["winning_fingerprint"],time.time()))
        self.conn.commit()
    def heartbeat(self,status="ok",details=None):
        self.conn.execute("INSERT INTO heartbeats(ts,status,details_json) VALUES(?,?,?)",(time.time(),status,json.dumps(details or {}))); self.conn.commit()
    def stats(self):
        return {"observer_events":self.conn.execute("SELECT COUNT(*) n FROM observer_events").fetchone()["n"],"issued_identities":self.conn.execute("SELECT COUNT(*) n FROM identity_registry").fetchone()["n"],"consensus_decisions":self.conn.execute("SELECT COUNT(*) n FROM consensus_decisions").fetchone()["n"],"duplicate_hashes":self.conn.execute("SELECT COUNT(*) n FROM duplicate_events WHERE hits>1").fetchone()["n"],"heartbeats":self.conn.execute("SELECT COUNT(*) n FROM heartbeats").fetchone()["n"],"by_severity":{r["severity"]:r["n"] for r in self.conn.execute("SELECT severity,COUNT(*) n FROM consensus_decisions GROUP BY severity")},"db_integrity":self.conn.execute("PRAGMA integrity_check").fetchone()[0]}
    def registry(self):
        return [dict(r) for r in self.conn.execute("SELECT person_id,legal_name,address,status,fingerprint FROM identity_registry ORDER BY person_id")]

class ShadowQueenDMV:
    def __init__(self,store,quorum=3):
        self.store=store; self.consensus=VirtualDMVConsensus(quorum)
    def process(self,events):
        for ev in events: self.store.record_observer_event(ev)
        decisions=self.consensus.evaluate(events)
        for d in decisions: self.store.record_decision(d)
        self.store.heartbeat("ok",{"processed":len(events),"decisions":len(decisions)})
        return decisions
