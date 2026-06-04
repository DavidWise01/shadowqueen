
import json, hashlib, sqlite3, time, zipfile
from pathlib import Path
from dataclasses import dataclass
from collections import Counter, defaultdict

def digest(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,default=str).encode()).hexdigest()

@dataclass(frozen=True)
class IdentityRecord:
    person_id:str; legal_name:str; address:str; dob:str=""; document_id:str=""; status:str="active"
    @classmethod
    def from_dict(cls,d):
        return cls(str(d["person_id"]),str(d.get("legal_name","")),str(d.get("address","")),str(d.get("dob","")),str(d.get("document_id","")),str(d.get("status","active")))
    def canonical(self):
        return {"person_id":self.person_id,"legal_name":self.legal_name.strip().lower(),"address":self.address.strip().lower(),"dob":self.dob,"document_id":self.document_id,"status":self.status}
    def fingerprint(self): return digest(self.canonical())

@dataclass(frozen=True)
class ObserverEvent:
    observer_id:str; record:IdentityRecord; role:str="clerk"
    @classmethod
    def from_dict(cls,d):
        return cls(str(d["observer_id"]),IdentityRecord.from_dict(d["record"]),str(d.get("role","clerk")))

class Store:
    def __init__(self,path="shadowqueen_dmv.db",office_id="local"):
        self.office_id=office_id
        self.conn=sqlite3.connect(Path(path)); self.conn.row_factory=sqlite3.Row
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS identity_registry(person_id TEXT PRIMARY KEY,legal_name TEXT,address TEXT,dob TEXT,document_id TEXT,status TEXT,fingerprint TEXT,office_id TEXT,issued_ts REAL);
        CREATE TABLE IF NOT EXISTS decisions(id INTEGER PRIMARY KEY,ts REAL,person_id TEXT,action TEXT,reason TEXT,severity TEXT,details_json TEXT);
        CREATE TABLE IF NOT EXISTS conflicts(id INTEGER PRIMARY KEY,ts REAL,person_id TEXT,local_fp TEXT,remote_fp TEXT,remote_office TEXT,details_json TEXT);
        CREATE TABLE IF NOT EXISTS audits(id INTEGER PRIMARY KEY,ts REAL,auditor_id TEXT,result TEXT,details_json TEXT);
        CREATE TABLE IF NOT EXISTS trust_ledger(seq INTEGER PRIMARY KEY AUTOINCREMENT,ts REAL,kind TEXT,subject TEXT,payload_hash TEXT,prev_hash TEXT,entry_hash TEXT,receipt_json TEXT);
        """); self.conn.commit()
    def last_hash(self):
        r=self.conn.execute("SELECT entry_hash FROM trust_ledger ORDER BY seq DESC LIMIT 1").fetchone()
        return r["entry_hash"] if r else "GENESIS"
    def receipt(self,kind,subject,payload):
        prev=self.last_hash(); ph=digest(payload); eh=digest({"kind":kind,"subject":subject,"payload_hash":ph,"prev_hash":prev})
        rec={"kind":kind,"subject":subject,"payload_hash":ph,"prev_hash":prev,"entry_hash":eh,"office_id":self.office_id,"ts":time.time()}
        self.conn.execute("INSERT INTO trust_ledger(ts,kind,subject,payload_hash,prev_hash,entry_hash,receipt_json) VALUES(?,?,?,?,?,?,?)",(rec["ts"],kind,subject,ph,prev,eh,json.dumps(rec,sort_keys=True)))
        self.conn.commit(); return rec
    def verify_ledger(self):
        prev="GENESIS"; n=0
        for r in self.conn.execute("SELECT seq,kind,subject,payload_hash,prev_hash,entry_hash FROM trust_ledger ORDER BY seq"):
            expected=digest({"kind":r["kind"],"subject":r["subject"],"payload_hash":r["payload_hash"],"prev_hash":prev})
            if r["prev_hash"]!=prev: return {"ok":False,"seq":r["seq"],"reason":"prev_hash_mismatch"}
            if r["entry_hash"]!=expected: return {"ok":False,"seq":r["seq"],"reason":"entry_hash_mismatch"}
            prev=r["entry_hash"]; n+=1
        return {"ok":True,"entries":n,"head":prev}
    def issue(self,record):
        fp=record.fingerprint(); c=record.canonical()
        self.conn.execute("INSERT OR REPLACE INTO identity_registry VALUES(?,?,?,?,?,?,?,?,?)",(c["person_id"],c["legal_name"],c["address"],c["dob"],c["document_id"],c["status"],fp,self.office_id,time.time()))
        self.receipt("identity_issued",record.person_id,{"identity":c,"fingerprint":fp})
        self.conn.commit(); return fp
    def decision(self,d):
        self.conn.execute("INSERT INTO decisions(ts,person_id,action,reason,severity,details_json) VALUES(?,?,?,?,?,?)",(time.time(),d["person_id"],d["action"],d["reason"],d["severity"],json.dumps(d)))
        self.receipt("decision",d["person_id"],d); self.conn.commit()
    def registry(self):
        return [dict(r) for r in self.conn.execute("SELECT person_id,legal_name,address,status,fingerprint,office_id FROM identity_registry ORDER BY person_id")]
    def conflict(self,pid,local_fp,remote_fp,remote_office,details):
        self.conn.execute("INSERT INTO conflicts(ts,person_id,local_fp,remote_fp,remote_office,details_json) VALUES(?,?,?,?,?,?)",(time.time(),pid,local_fp,remote_fp,remote_office,json.dumps(details)))
        self.receipt("conflict",pid,details); self.conn.commit()
    def audit(self,auditor,result,details):
        self.conn.execute("INSERT INTO audits(ts,auditor_id,result,details_json) VALUES(?,?,?,?)",(time.time(),auditor,result,json.dumps(details)))
        self.receipt("audit",auditor,{"result":result,"details":details}); self.conn.commit()
    def stats(self):
        return {"office_id":self.office_id,"issued_identities":self.conn.execute("SELECT COUNT(*) n FROM identity_registry").fetchone()["n"],"decisions":self.conn.execute("SELECT COUNT(*) n FROM decisions").fetchone()["n"],"conflicts":self.conn.execute("SELECT COUNT(*) n FROM conflicts").fetchone()["n"],"audits":self.conn.execute("SELECT COUNT(*) n FROM audits").fetchone()["n"],"ledger":self.verify_ledger(),"db_integrity":self.conn.execute("PRAGMA integrity_check").fetchone()[0]}
    def bundle(self,out):
        out=Path(out)
        with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
            for table in ["identity_registry","decisions","conflicts","audits","trust_ledger"]:
                rows=[dict(r) for r in self.conn.execute(f"SELECT * FROM {table} ORDER BY 1")]
                z.writestr(f"{table}.json",json.dumps(rows,indent=2,default=str))
            z.writestr("manifest.json",json.dumps({"stats":self.stats(),"created":time.time()},indent=2))
        return {"bundle":str(out),"exists":out.exists()}

class ConsensusDMV:
    def __init__(self,store,quorum=3): self.store=store; self.quorum=quorum
    def process(self,events):
        grouped=defaultdict(list)
        for ev in events: grouped[ev.record.person_id].append(ev)
        out=[]
        for pid,evs in grouped.items():
            votes=Counter(ev.record.fingerprint() for ev in evs); fp,n=votes.most_common(1)[0]
            if n>=self.quorum and len(votes)==1:
                rec=next(ev.record for ev in evs if ev.record.fingerprint()==fp)
                self.store.issue(rec); d={"person_id":pid,"action":"issue_identity","reason":"quorum_clean","severity":"info","fingerprint":fp}
            elif len(votes)>1: d={"person_id":pid,"action":"quarantine","reason":"local_dissent","severity":"high","votes":dict(votes)}
            else: d={"person_id":pid,"action":"track","reason":"insufficient_quorum","severity":"medium","votes":dict(votes)}
            self.store.decision(d); out.append(d)
        return out

class FederationManager:
    def __init__(self,store): self.store=store
    def compare(self,remote_registry,remote_office="remote"):
        local={r["person_id"]:r for r in self.store.registry()}; conflicts=[]
        for r in remote_registry:
            if r["person_id"] in local and local[r["person_id"]]["fingerprint"]!=r["fingerprint"]:
                c={"person_id":r["person_id"],"local":local[r["person_id"]],"remote":r,"remote_office":remote_office}
                self.store.conflict(r["person_id"],local[r["person_id"]]["fingerprint"],r["fingerprint"],remote_office,c); conflicts.append(c)
        result={"conflicts":len(conflicts),"remote_office":remote_office}
        self.store.audit("federation-manager","pass" if not conflicts else "conflict",result)
        return {"summary":result,"conflicts":conflicts}

class ExternalAuditor:
    def __init__(self,store,auditor_id="auditor-1"): self.store=store; self.auditor_id=auditor_id
    def review(self):
        st=self.store.stats(); result="pass"; notes=[]
        if not st["ledger"]["ok"]: result="fail"; notes.append("ledger_failed")
        if st["conflicts"]>0 and result!="fail": result="warning"; notes.append("open_conflicts")
        details={"stats":st,"notes":notes}
        self.store.audit(self.auditor_id,result,details)
        return {"auditor_id":self.auditor_id,"result":result,"details":details}
