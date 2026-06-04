
import json, hashlib, sqlite3, time, zipfile
from dataclasses import dataclass
from collections import Counter, defaultdict
from pathlib import Path

@dataclass(frozen=True)
class IdentityRecord:
    person_id:str; legal_name:str; address:str; dob:str=""; document_id:str=""; status:str="active"; office_id:str="local"
    @classmethod
    def from_dict(cls,d):
        return cls(str(d["person_id"]),str(d.get("legal_name","")),str(d.get("address","")),str(d.get("dob","")),str(d.get("document_id","")),str(d.get("status","active")),str(d.get("office_id","local")))
    def canonical(self):
        return {"person_id":self.person_id,"legal_name":self.legal_name.strip().lower(),"address":self.address.strip().lower(),"dob":self.dob,"document_id":self.document_id,"status":self.status}
    def fingerprint(self):
        return hashlib.sha256(json.dumps(self.canonical(),sort_keys=True).encode()).hexdigest()

@dataclass(frozen=True)
class ObserverEvent:
    observer_id:str; record:IdentityRecord; role:str="clerk"; office_id:str="local"
    @classmethod
    def from_dict(cls,d):
        r=IdentityRecord.from_dict(d["record"])
        return cls(str(d["observer_id"]),r,str(d.get("role","clerk")),str(d.get("office_id",r.office_id)))

class Store:
    def __init__(self,path="shadowqueen_dmv.db",office_id="local"):
        self.office_id=office_id
        self.conn=sqlite3.connect(Path(path)); self.conn.row_factory=sqlite3.Row
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS identity_registry(person_id TEXT PRIMARY KEY,legal_name TEXT,address TEXT,dob TEXT,document_id TEXT,status TEXT,fingerprint TEXT,office_id TEXT,issued_ts REAL);
        CREATE TABLE IF NOT EXISTS observer_events(id INTEGER PRIMARY KEY,ts REAL,office_id TEXT,observer_id TEXT,person_id TEXT,record_fp TEXT);
        CREATE TABLE IF NOT EXISTS decisions(id INTEGER PRIMARY KEY,ts REAL,office_id TEXT,person_id TEXT,action TEXT,reason TEXT,severity TEXT,details_json TEXT);
        CREATE TABLE IF NOT EXISTS federation_conflicts(id INTEGER PRIMARY KEY,ts REAL,person_id TEXT,local_fp TEXT,remote_fp TEXT,remote_office TEXT,status TEXT,details_json TEXT);
        CREATE TABLE IF NOT EXISTS audit_reviews(id INTEGER PRIMARY KEY,ts REAL,auditor_id TEXT,scope TEXT,result TEXT,details_json TEXT);
        CREATE TABLE IF NOT EXISTS evidence_log(id INTEGER PRIMARY KEY,ts REAL,kind TEXT,person_id TEXT,details_json TEXT);
        """); self.conn.commit()
    def evidence(self,kind,pid,details):
        self.conn.execute("INSERT INTO evidence_log(ts,kind,person_id,details_json) VALUES(?,?,?,?)",(time.time(),kind,pid,json.dumps(details,default=str)))
    def issue(self,record):
        fp=record.fingerprint(); c=record.canonical()
        self.conn.execute("INSERT OR REPLACE INTO identity_registry VALUES(?,?,?,?,?,?,?,?,?)",(c["person_id"],c["legal_name"],c["address"],c["dob"],c["document_id"],c["status"],fp,self.office_id,time.time()))
        self.evidence("identity_issued",record.person_id,{"fingerprint":fp,"office":self.office_id})
        self.conn.commit()
        return fp
    def registry(self):
        return [dict(r) for r in self.conn.execute("SELECT person_id,legal_name,address,dob,document_id,status,fingerprint,office_id FROM identity_registry ORDER BY person_id")]
    def record_conflict(self,pid,local_fp,remote_fp,remote_office,details):
        self.conn.execute("INSERT INTO federation_conflicts(ts,person_id,local_fp,remote_fp,remote_office,status,details_json) VALUES(?,?,?,?,?,?,?)",(time.time(),pid,local_fp,remote_fp,remote_office,"open",json.dumps(details,default=str)))
        self.evidence("federation_conflict",pid,details); self.conn.commit()
    def audit(self,auditor_id,scope,result,details):
        self.conn.execute("INSERT INTO audit_reviews(ts,auditor_id,scope,result,details_json) VALUES(?,?,?,?,?)",(time.time(),auditor_id,scope,result,json.dumps(details,default=str)))
        self.evidence("audit_review",scope,{"auditor_id":auditor_id,"result":result,"details":details}); self.conn.commit()
    def stats(self):
        return {"office_id":self.office_id,"issued_identities":self.conn.execute("SELECT COUNT(*) n FROM identity_registry").fetchone()["n"],"federation_conflicts":self.conn.execute("SELECT COUNT(*) n FROM federation_conflicts").fetchone()["n"],"audit_reviews":self.conn.execute("SELECT COUNT(*) n FROM audit_reviews").fetchone()["n"],"evidence":self.conn.execute("SELECT COUNT(*) n FROM evidence_log").fetchone()["n"],"db_integrity":self.conn.execute("PRAGMA integrity_check").fetchone()[0]}
    def bundle(self,out):
        out=Path(out)
        with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
            for table in ["identity_registry","federation_conflicts","audit_reviews","evidence_log"]:
                rows=[dict(r) for r in self.conn.execute(f"SELECT * FROM {table} ORDER BY 1")]
                z.writestr(f"{table}.json",json.dumps(rows,indent=2,default=str))
            z.writestr("manifest.json",json.dumps({"stats":self.stats(),"created":time.time()},indent=2))
        return {"bundle":str(out),"exists":out.exists()}

class ConsensusDMV:
    def __init__(self,store,quorum=3): self.store=store; self.quorum=quorum
    def process(self,events):
        grouped=defaultdict(list)
        for ev in events:
            grouped[ev.record.person_id].append(ev)
            self.store.conn.execute("INSERT INTO observer_events(ts,office_id,observer_id,person_id,record_fp) VALUES(?,?,?,?,?)",(time.time(),ev.office_id,ev.observer_id,ev.record.person_id,ev.record.fingerprint()))
        decisions=[]
        for pid,evs in grouped.items():
            votes=Counter(ev.record.fingerprint() for ev in evs)
            fp,n=votes.most_common(1)[0]
            if n>=self.quorum and len(votes)==1:
                rec=next(ev.record for ev in evs if ev.record.fingerprint()==fp)
                self.store.issue(rec)
                d={"person_id":pid,"action":"issue_identity","reason":"quorum_clean","severity":"info","fingerprint":fp}
            elif len(votes)>1:
                d={"person_id":pid,"action":"quarantine","reason":"local_dissent","severity":"high","votes":dict(votes)}
            else:
                d={"person_id":pid,"action":"track","reason":"insufficient_quorum","severity":"medium","votes":dict(votes)}
            self.store.conn.execute("INSERT INTO decisions(ts,office_id,person_id,action,reason,severity,details_json) VALUES(?,?,?,?,?,?,?)",(time.time(),self.store.office_id,pid,d["action"],d["reason"],d["severity"],json.dumps(d)))
            decisions.append(d)
        self.store.conn.commit()
        return decisions

class FederationManager:
    def __init__(self,store): self.store=store
    def compare(self,remote_registry,remote_office="remote"):
        local={r["person_id"]:r for r in self.store.registry()}
        conflicts=[]; imports=[]
        for r in remote_registry:
            pid=r["person_id"]
            if pid not in local:
                imports.append(r); continue
            if local[pid]["fingerprint"]!=r["fingerprint"]:
                c={"person_id":pid,"local":local[pid],"remote":r,"remote_office":remote_office}
                self.store.record_conflict(pid,local[pid]["fingerprint"],r["fingerprint"],remote_office,c)
                conflicts.append(c)
        result={"remote_office":remote_office,"conflicts":len(conflicts),"imports":len(imports)}
        self.store.audit("federation-manager","registry_sync","pass" if not conflicts else "conflict",result)
        return {"summary":result,"conflicts":conflicts,"imports":imports}

class ExternalAuditor:
    def __init__(self,store,auditor_id="auditor-1"): self.store=store; self.auditor_id=auditor_id
    def review(self):
        st=self.store.stats()
        notes=[]
        result="pass"
        if st["db_integrity"]!="ok": result="fail"; notes.append("db_integrity_failed")
        if st["federation_conflicts"]>0 and result!="fail": result="warning"; notes.append("open_federation_conflicts")
        details={"stats":st,"notes":notes}
        self.store.audit(self.auditor_id,"full_registry",result,details)
        return {"auditor_id":self.auditor_id,"result":result,"details":details}
