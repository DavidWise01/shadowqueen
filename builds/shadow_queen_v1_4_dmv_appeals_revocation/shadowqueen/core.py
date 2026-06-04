
from dataclasses import dataclass
from collections import Counter, defaultdict
import json, hashlib, sqlite3, time, zipfile
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
    record:IdentityRecord
    role:str="clerk"
    confidence:float=1.0
    @classmethod
    def from_dict(cls,d):
        return cls(str(d["observer_id"]),IdentityRecord.from_dict(d["record"]),str(d.get("role","clerk")),float(d.get("confidence",1.0)))
    def event_hash(self):
        return hashlib.sha256(json.dumps({"observer_id":self.observer_id,"role":self.role,"record_fp":self.record.fingerprint(),"confidence":round(self.confidence,4)},sort_keys=True).encode()).hexdigest()

class Consensus:
    def __init__(self,quorum=3): self.quorum=quorum
    def evaluate(self,events):
        grouped=defaultdict(list)
        for ev in events: grouped[ev.record.person_id].append(ev)
        out=[]
        for pid, evs in grouped.items():
            votes=Counter(ev.record.fingerprint() for ev in evs)
            fp,n=votes.most_common(1)[0]
            dissent=[ev for ev in evs if ev.record.fingerprint()!=fp]
            sample=next(ev.record for ev in evs if ev.record.fingerprint()==fp)
            if len({ev.observer_id for ev in evs})!=len(evs):
                action,reason,severity="quarantine","duplicate_observer_vote","high"
            elif n>=self.quorum and not dissent:
                action,reason,severity="issue_identity","quorum_clean","info"
            elif n>=self.quorum and dissent:
                action,reason,severity="track","quorum_with_dissent","medium"
            elif dissent:
                action,reason,severity="quarantine","identity_disagreement_no_quorum","high"
            else:
                action,reason,severity="track","insufficient_quorum","medium"
            out.append({"person_id":pid,"action":action,"reason":reason,"severity":severity,"winning_fingerprint":fp,"winning_votes":n,"quorum":self.quorum,"observer_count":len(evs),"identity":sample.canonical(),"dissenters":[ev.observer_id for ev in dissent]})
        return out

class Store:
    def __init__(self,path="shadowqueen_dmv.db"):
        self.conn=sqlite3.connect(Path(path)); self.conn.row_factory=sqlite3.Row
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS observer_events(id INTEGER PRIMARY KEY,ts REAL,observer_id TEXT,role TEXT,person_id TEXT,record_fingerprint TEXT,event_hash TEXT);
        CREATE TABLE IF NOT EXISTS identity_registry(person_id TEXT PRIMARY KEY,legal_name TEXT,address TEXT,dob TEXT,document_id TEXT,status TEXT,fingerprint TEXT,issued_ts REAL,updated_ts REAL);
        CREATE TABLE IF NOT EXISTS consensus_decisions(id INTEGER PRIMARY KEY,ts REAL,person_id TEXT,action TEXT,reason TEXT,severity TEXT,decision_json TEXT);
        CREATE TABLE IF NOT EXISTS appeals(id INTEGER PRIMARY KEY,ts REAL,appeal_id TEXT UNIQUE,person_id TEXT,reason TEXT,status TEXT,details_json TEXT);
        CREATE TABLE IF NOT EXISTS revocations(id INTEGER PRIMARY KEY,ts REAL,person_id TEXT,old_status TEXT,new_status TEXT,reason TEXT,details_json TEXT);
        CREATE TABLE IF NOT EXISTS evidence_log(id INTEGER PRIMARY KEY,ts REAL,kind TEXT,person_id TEXT,details_json TEXT);
        """); self.conn.commit()
    def evidence(self,kind,pid,details):
        self.conn.execute("INSERT INTO evidence_log(ts,kind,person_id,details_json) VALUES(?,?,?,?)",(time.time(),kind,pid,json.dumps(details,default=str)))
    def record_observer_event(self,ev):
        self.conn.execute("INSERT INTO observer_events(ts,observer_id,role,person_id,record_fingerprint,event_hash) VALUES(?,?,?,?,?,?)",(time.time(),ev.observer_id,ev.role,ev.record.person_id,ev.record.fingerprint(),ev.event_hash()))
        self.conn.commit()
    def record_decision(self,d):
        self.conn.execute("INSERT INTO consensus_decisions(ts,person_id,action,reason,severity,decision_json) VALUES(?,?,?,?,?,?)",(time.time(),d["person_id"],d["action"],d["reason"],d["severity"],json.dumps(d)))
        if d["action"]=="issue_identity":
            i=d["identity"]; now=time.time()
            self.conn.execute("INSERT OR REPLACE INTO identity_registry(person_id,legal_name,address,dob,document_id,status,fingerprint,issued_ts,updated_ts) VALUES(?,?,?,?,?,?,?,?,?)",(i["person_id"],i["legal_name"],i["address"],i["dob"],i["document_id"],"active",d["winning_fingerprint"],now,now))
            self.evidence("identity_issued",i["person_id"],d)
        self.conn.commit()
    def create_appeal(self,appeal_id,pid,reason):
        self.conn.execute("INSERT INTO appeals(ts,appeal_id,person_id,reason,status,details_json) VALUES(?,?,?,?,?,?)",(time.time(),appeal_id,pid,reason,"open","{}"))
        self.evidence("appeal_opened",pid,{"appeal_id":appeal_id,"reason":reason})
        self.conn.commit()
        return {"appeal_id":appeal_id,"person_id":pid,"status":"open"}
    def set_status(self,pid,status,reason,details=None):
        row=self.conn.execute("SELECT status FROM identity_registry WHERE person_id=?",(pid,)).fetchone()
        old=row["status"] if row else "missing"
        self.conn.execute("UPDATE identity_registry SET status=?,updated_ts=? WHERE person_id=?",(status,time.time(),pid))
        self.conn.execute("INSERT INTO revocations(ts,person_id,old_status,new_status,reason,details_json) VALUES(?,?,?,?,?,?)",(time.time(),pid,old,status,reason,json.dumps(details or {})))
        self.evidence("status_change",pid,{"old":old,"new":status,"reason":reason})
        self.conn.commit()
        return {"person_id":pid,"old_status":old,"new_status":status}
    def close_appeal(self,appeal_id,status,details=None):
        self.conn.execute("UPDATE appeals SET status=?,details_json=? WHERE appeal_id=?",(status,json.dumps(details or {}),appeal_id))
        row=self.conn.execute("SELECT person_id FROM appeals WHERE appeal_id=?",(appeal_id,)).fetchone()
        self.evidence("appeal_closed",row["person_id"] if row else "",{"appeal_id":appeal_id,"status":status})
        self.conn.commit()
    def stats(self):
        return {"observer_events":self.conn.execute("SELECT COUNT(*) n FROM observer_events").fetchone()["n"],"issued_identities":self.conn.execute("SELECT COUNT(*) n FROM identity_registry").fetchone()["n"],"decisions":self.conn.execute("SELECT COUNT(*) n FROM consensus_decisions").fetchone()["n"],"appeals":self.conn.execute("SELECT COUNT(*) n FROM appeals").fetchone()["n"],"revocations":self.conn.execute("SELECT COUNT(*) n FROM revocations").fetchone()["n"],"evidence":self.conn.execute("SELECT COUNT(*) n FROM evidence_log").fetchone()["n"],"db_integrity":self.conn.execute("PRAGMA integrity_check").fetchone()[0]}
    def registry(self):
        return [dict(r) for r in self.conn.execute("SELECT person_id,legal_name,address,status,fingerprint FROM identity_registry ORDER BY person_id")]
    def appeals(self):
        return [dict(r) for r in self.conn.execute("SELECT appeal_id,person_id,reason,status FROM appeals ORDER BY id DESC")]
    def evidence_bundle(self,out_path):
        out=Path(out_path)
        with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
            z.writestr("manifest.json",json.dumps({"stats":self.stats(),"registry":self.registry(),"appeals":self.appeals(),"created":time.time()},indent=2))
            z.writestr("evidence_log.json",json.dumps([dict(r) for r in self.conn.execute("SELECT * FROM evidence_log ORDER BY id")],indent=2))
        return {"bundle":str(out),"exists":out.exists()}

class ShadowQueenDMV:
    def __init__(self,store,quorum=3):
        self.store=store; self.consensus=Consensus(quorum)
    def process(self,events):
        for ev in events: self.store.record_observer_event(ev)
        decisions=self.consensus.evaluate(events)
        for d in decisions: self.store.record_decision(d)
        return decisions
    def appeal_review(self,appeal_id,pid,events):
        self.store.set_status(pid,"suspended","appeal_under_review",{"appeal_id":appeal_id})
        decision=next((d for d in self.process(events) if d["person_id"]==pid),None)
        if decision and decision["action"]=="issue_identity":
            self.store.set_status(pid,"active","appeal_restored",{"appeal_id":appeal_id})
            self.store.close_appeal(appeal_id,"restored",decision)
            return {"appeal_id":appeal_id,"result":"restored","decision":decision}
        self.store.set_status(pid,"revoked","appeal_failed_or_no_quorum",{"appeal_id":appeal_id})
        self.store.close_appeal(appeal_id,"revoked",decision or {})
        return {"appeal_id":appeal_id,"result":"revoked","decision":decision}
