
import json, hashlib, sqlite3, time, zipfile
from pathlib import Path
from dataclasses import dataclass, field

def digest(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,default=str).encode()).hexdigest()

@dataclass(frozen=True)
class Credential:
    credential_id:str
    subject_id:str
    credential_type:str="identity"
    status:str="issued"
    issued_ts:float=0.0
    expires_ts:float=0.0
    proof_hash:str=""
    metadata:dict=field(default_factory=dict)

    @classmethod
    def create(cls, credential_id, subject_id, credential_type="identity", ttl_days=365, proof_hash="", metadata=None):
        now=time.time()
        return cls(credential_id,subject_id,credential_type,"issued",now,now+ttl_days*86400,proof_hash,metadata or {})

    def fingerprint(self):
        return digest({"credential_id":self.credential_id,"subject_id":self.subject_id,"credential_type":self.credential_type,"issued_ts":self.issued_ts,"expires_ts":self.expires_ts,"proof_hash":self.proof_hash})

class Store:
    def __init__(self,path="credentials.db",node_id="queen"):
        self.node_id=node_id
        self.conn=sqlite3.connect(Path(path)); self.conn.row_factory=sqlite3.Row
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS credentials(credential_id TEXT PRIMARY KEY,subject_id TEXT,credential_type TEXT,status TEXT,issued_ts REAL,expires_ts REAL,proof_hash TEXT,fingerprint TEXT,metadata_json TEXT,updated_ts REAL);
        CREATE TABLE IF NOT EXISTS credential_history(id INTEGER PRIMARY KEY,ts REAL,credential_id TEXT,action TEXT,from_status TEXT,to_status TEXT,actor TEXT,reason TEXT,details_json TEXT);
        CREATE TABLE IF NOT EXISTS custody_chain(id INTEGER PRIMARY KEY,ts REAL,credential_id TEXT,from_actor TEXT,to_actor TEXT,action TEXT,custody_hash TEXT,details_json TEXT);
        CREATE TABLE IF NOT EXISTS lifecycle_findings(id INTEGER PRIMARY KEY,ts REAL,credential_id TEXT,kind TEXT,severity TEXT,details_json TEXT);
        CREATE TABLE IF NOT EXISTS ledger(seq INTEGER PRIMARY KEY AUTOINCREMENT,ts REAL,kind TEXT,subject TEXT,payload_hash TEXT,prev_hash TEXT,entry_hash TEXT);
        """); self.conn.commit()

    def last_hash(self):
        r=self.conn.execute("SELECT entry_hash FROM ledger ORDER BY seq DESC LIMIT 1").fetchone()
        return r["entry_hash"] if r else "GENESIS"

    def receipt(self,kind,subject,payload):
        prev=self.last_hash(); ph=digest(payload); eh=digest({"kind":kind,"subject":subject,"payload_hash":ph,"prev_hash":prev})
        self.conn.execute("INSERT INTO ledger(ts,kind,subject,payload_hash,prev_hash,entry_hash) VALUES(?,?,?,?,?,?)",(time.time(),kind,subject,ph,prev,eh)); self.conn.commit()

    def verify_ledger(self):
        prev="GENESIS"; n=0
        for r in self.conn.execute("SELECT seq,kind,subject,payload_hash,prev_hash,entry_hash FROM ledger ORDER BY seq"):
            exp=digest({"kind":r["kind"],"subject":r["subject"],"payload_hash":r["payload_hash"],"prev_hash":prev})
            if r["prev_hash"]!=prev: return {"ok":False,"seq":r["seq"],"reason":"prev_hash_mismatch"}
            if r["entry_hash"]!=exp: return {"ok":False,"seq":r["seq"],"reason":"entry_hash_mismatch"}
            prev=r["entry_hash"]; n+=1
        return {"ok":True,"entries":n,"head":prev}

    def get(self,cid):
        r=self.conn.execute("SELECT * FROM credentials WHERE credential_id=?",(cid,)).fetchone()
        return dict(r) if r else None

    def history_event(self,cid,action,old,new,actor,reason,details=None):
        self.conn.execute("INSERT INTO credential_history(ts,credential_id,action,from_status,to_status,actor,reason,details_json) VALUES(?,?,?,?,?,?,?,?)",(time.time(),cid,action,old,new,actor,reason,json.dumps(details or {},default=str)))
        self.receipt("credential_history",cid,{"action":action,"from":old,"to":new,"actor":actor,"reason":reason})

    def custody(self,cid,src,dst,action,details=None):
        payload={"credential_id":cid,"from_actor":src,"to_actor":dst,"action":action,"details":details or {},"ts":time.time()}
        ch=digest(payload)
        self.conn.execute("INSERT INTO custody_chain(ts,credential_id,from_actor,to_actor,action,custody_hash,details_json) VALUES(?,?,?,?,?,?,?)",(payload["ts"],cid,src,dst,action,ch,json.dumps(details or {},default=str)))
        self.receipt("custody",cid,{"custody_hash":ch})

    def finding(self,cid,kind,severity,details):
        self.conn.execute("INSERT INTO lifecycle_findings(ts,credential_id,kind,severity,details_json) VALUES(?,?,?,?,?)",(time.time(),cid,kind,severity,json.dumps(details,default=str)))
        self.receipt("finding",cid,{"kind":kind,"severity":severity})

    def credentials(self):
        return [dict(r) for r in self.conn.execute("SELECT credential_id,subject_id,credential_type,status,issued_ts,expires_ts,proof_hash,fingerprint FROM credentials ORDER BY credential_id")]

    def history(self,cid=None):
        if cid: rows=self.conn.execute("SELECT * FROM credential_history WHERE credential_id=? ORDER BY id",(cid,))
        else: rows=self.conn.execute("SELECT * FROM credential_history ORDER BY id")
        return [dict(r) for r in rows]

    def findings(self):
        return [dict(r) for r in self.conn.execute("SELECT credential_id,kind,severity,details_json FROM lifecycle_findings ORDER BY id")]

    def stats(self):
        return {"node_id":self.node_id,"credentials":self.conn.execute("SELECT COUNT(*) n FROM credentials").fetchone()["n"],"history":self.conn.execute("SELECT COUNT(*) n FROM credential_history").fetchone()["n"],"custody":self.conn.execute("SELECT COUNT(*) n FROM custody_chain").fetchone()["n"],"findings":self.conn.execute("SELECT COUNT(*) n FROM lifecycle_findings").fetchone()["n"],"ledger":self.verify_ledger(),"db_integrity":self.conn.execute("PRAGMA integrity_check").fetchone()[0]}

    def bundle(self,out):
        out=Path(out)
        with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
            for table in ["credentials","credential_history","custody_chain","lifecycle_findings","ledger"]:
                rows=[dict(r) for r in self.conn.execute(f"SELECT * FROM {table} ORDER BY 1")]
                z.writestr(f"{table}.json",json.dumps(rows,indent=2,default=str))
            z.writestr("manifest.json",json.dumps({"stats":self.stats(),"created":time.time()},indent=2))
        return {"bundle":str(out),"exists":out.exists()}

class CredentialLifecycle:
    VALID={"active","suspended","revoked","expired","replaced"}
    def __init__(self,store): self.store=store

    def issue(self,c,actor="queen",reason="initial issuance"):
        fp=c.fingerprint()
        self.store.conn.execute("INSERT OR REPLACE INTO credentials VALUES(?,?,?,?,?,?,?,?,?,?)",(c.credential_id,c.subject_id,c.credential_type,"active",c.issued_ts,c.expires_ts,c.proof_hash,fp,json.dumps(c.metadata),time.time()))
        self.store.history_event(c.credential_id,"issue","none","active",actor,reason,{"fingerprint":fp})
        self.store.custody(c.credential_id,actor,c.subject_id,"issued",{"fingerprint":fp})
        self.store.conn.commit()
        return {"ok":True,"credential_id":c.credential_id,"status":"active","fingerprint":fp}

    def transition(self,cid,to_status,actor="queen",reason="",details=None):
        cur=self.store.get(cid)
        if not cur: return {"ok":False,"reason":"missing_credential"}
        old=cur["status"]
        if to_status not in self.VALID: return {"ok":False,"reason":"bad_status"}
        if (old,to_status) in {("revoked","active"),("expired","active"),("replaced","active")}:
            self.store.finding(cid,"invalid_lifecycle_transition","high",{"from":old,"to":to_status,"actor":actor})
            return {"ok":False,"reason":"invalid_transition","from":old,"to":to_status}
        self.store.conn.execute("UPDATE credentials SET status=?,updated_ts=? WHERE credential_id=?",(to_status,time.time(),cid))
        self.store.history_event(cid,"transition",old,to_status,actor,reason,details or {})
        self.store.custody(cid,actor,cur["subject_id"],to_status,details or {})
        self.store.conn.commit()
        return {"ok":True,"credential_id":cid,"from":old,"to":to_status}

    def suspend(self,cid,actor="queen",reason="suspended"): return self.transition(cid,"suspended",actor,reason)
    def revoke(self,cid,actor="queen",reason="revoked"): return self.transition(cid,"revoked",actor,reason)

    def expire_due(self,actor="scheduler"):
        now=time.time(); out=[]
        for c in self.store.credentials():
            if c["status"]=="active" and c["expires_ts"]<now:
                out.append(self.transition(c["credential_id"],"expired",actor,"expiration reached"))
        return out

    def renew(self,cid,new_id,ttl_days=365,actor="queen",reason="renewal"):
        cur=self.store.get(cid)
        if not cur: return {"ok":False,"reason":"missing_credential"}
        self.transition(cid,"replaced",actor,reason,{"replacement":new_id})
        new=Credential.create(new_id,cur["subject_id"],cur["credential_type"],ttl_days,cur["proof_hash"],{"renewed_from":cid})
        issued=self.issue(new,actor,reason)
        self.store.custody(cid,cid,new_id,"renewed_to",{"new":new_id})
        return {"ok":True,"old":cid,"new":issued}

    def audit(self):
        now=time.time()
        for c in self.store.credentials():
            if c["status"]=="active" and c["expires_ts"]<now:
                self.store.finding(c["credential_id"],"active_but_expired","high",c)
        return {"stats":self.store.stats(),"findings":self.store.findings()}
