
import json, hashlib, sqlite3, time, zipfile
from pathlib import Path
from dataclasses import dataclass

def digest(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,default=str).encode()).hexdigest()

@dataclass(frozen=True)
class Actor:
    actor_id:str
    role:str="clerk"
    trust_score:float=0.5

@dataclass(frozen=True)
class Credential:
    credential_id:str
    subject_id:str
    credential_type:str="identity"
    issued_ts:float=0.0
    expires_ts:float=0.0
    proof_hash:str=""
    @classmethod
    def create(cls,cid,subject,ctype="identity",ttl_days=365,proof_hash=""):
        now=time.time()
        return cls(cid,subject,ctype,now,now+(ttl_days*86400),proof_hash)
    def fingerprint(self):
        return digest(self.__dict__)

class Store:
    def __init__(self,path="policy.db",node_id="queen"):
        self.node_id=node_id
        self.conn=sqlite3.connect(Path(path))
        self.conn.row_factory=sqlite3.Row
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS credentials(credential_id TEXT PRIMARY KEY,subject_id TEXT,credential_type TEXT,status TEXT,issued_ts REAL,expires_ts REAL,proof_hash TEXT,fingerprint TEXT,updated_ts REAL);
        CREATE TABLE IF NOT EXISTS policy_rules(rule_id TEXT PRIMARY KEY,action TEXT,role TEXT,allow INTEGER,conditions_json TEXT,reason TEXT,priority INTEGER);
        CREATE TABLE IF NOT EXISTS policy_decisions(id INTEGER PRIMARY KEY,ts REAL,credential_id TEXT,action TEXT,actor_id TEXT,role TEXT,allowed INTEGER,reason TEXT,details_json TEXT);
        CREATE TABLE IF NOT EXISTS credential_history(id INTEGER PRIMARY KEY,ts REAL,credential_id TEXT,action TEXT,from_status TEXT,to_status TEXT,actor TEXT,reason TEXT);
        CREATE TABLE IF NOT EXISTS findings(id INTEGER PRIMARY KEY,ts REAL,credential_id TEXT,kind TEXT,severity TEXT,details_json TEXT);
        CREATE TABLE IF NOT EXISTS ledger(seq INTEGER PRIMARY KEY AUTOINCREMENT,ts REAL,kind TEXT,subject TEXT,payload_hash TEXT,prev_hash TEXT,entry_hash TEXT);
        """)
        self.conn.commit()
        self.seed()
    def seed(self):
        rules=[
        ("issue.registrar","issue","registrar",1,{"min_trust":0.6},"registrar may issue",100),
        ("issue.queen","issue","queen",1,{},"queen may issue",100),
        ("issue.clerk.deny","issue","clerk",0,{},"clerk cannot issue",100),
        ("suspend.clerk","suspend","clerk",1,{"status":["active"]},"clerk may suspend active",100),
        ("suspend.registrar","suspend","registrar",1,{"status":["active"]},"registrar may suspend active",100),
        ("revoke.registrar","revoke","registrar",1,{"status":["active","suspended"]},"registrar may revoke",100),
        ("revoke.auditor","revoke","auditor",1,{"status":["suspended"],"requires_finding":1},"auditor may revoke suspended with finding",100),
        ("revoke.clerk.deny","revoke","clerk",0,{},"clerk cannot revoke",100),
        ("renew.registrar","renew","registrar",1,{"status":["active","suspended"],"window_days":90},"registrar may renew in window",100),
        ("renew.queen","renew","queen",1,{},"queen may renew",100),
        ]
        self.conn.executemany("INSERT OR IGNORE INTO policy_rules VALUES(?,?,?,?,?,?,?)",[(a,b,c,d,json.dumps(e),f,g) for a,b,c,d,e,f,g in rules])
        self.conn.commit()
    def last_hash(self):
        r=self.conn.execute("SELECT entry_hash FROM ledger ORDER BY seq DESC LIMIT 1").fetchone()
        return r["entry_hash"] if r else "GENESIS"
    def receipt(self,kind,subject,payload):
        prev=self.last_hash(); ph=digest(payload); eh=digest({"kind":kind,"subject":subject,"payload_hash":ph,"prev_hash":prev})
        self.conn.execute("INSERT INTO ledger(ts,kind,subject,payload_hash,prev_hash,entry_hash) VALUES(?,?,?,?,?,?)",(time.time(),kind,subject,ph,prev,eh))
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
    def policy_decision(self,cid,action,actor,allowed,reason,details):
        self.conn.execute("INSERT INTO policy_decisions(ts,credential_id,action,actor_id,role,allowed,reason,details_json) VALUES(?,?,?,?,?,?,?,?)",(time.time(),cid,action,actor.actor_id,actor.role,1 if allowed else 0,reason,json.dumps(details,default=str)))
        self.receipt("policy_decision",cid or action,{"action":action,"actor":actor.__dict__,"allowed":allowed,"reason":reason})
    def history(self,cid,action,old,new,actor,reason):
        self.conn.execute("INSERT INTO credential_history(ts,credential_id,action,from_status,to_status,actor,reason) VALUES(?,?,?,?,?,?,?)",(time.time(),cid,action,old,new,actor.actor_id,reason))
        self.receipt("credential_history",cid,{"action":action,"from":old,"to":new,"actor":actor.actor_id})
    def finding(self,cid,kind,severity,details):
        self.conn.execute("INSERT INTO findings(ts,credential_id,kind,severity,details_json) VALUES(?,?,?,?,?)",(time.time(),cid,kind,severity,json.dumps(details,default=str)))
        self.receipt("finding",cid,{"kind":kind,"severity":severity})
    def rules(self):
        return [dict(r) for r in self.conn.execute("SELECT * FROM policy_rules ORDER BY action,priority DESC")]
    def credentials(self):
        return [dict(r) for r in self.conn.execute("SELECT credential_id,subject_id,credential_type,status,expires_ts,proof_hash FROM credentials ORDER BY credential_id")]
    def policy_audit(self):
        return [dict(r) for r in self.conn.execute("SELECT credential_id,action,actor_id,role,allowed,reason FROM policy_decisions ORDER BY id")]
    def stats(self):
        return {"node_id":self.node_id,"credentials":self.conn.execute("SELECT COUNT(*) n FROM credentials").fetchone()["n"],"rules":self.conn.execute("SELECT COUNT(*) n FROM policy_rules").fetchone()["n"],"policy_decisions":self.conn.execute("SELECT COUNT(*) n FROM policy_decisions").fetchone()["n"],"history":self.conn.execute("SELECT COUNT(*) n FROM credential_history").fetchone()["n"],"findings":self.conn.execute("SELECT COUNT(*) n FROM findings").fetchone()["n"],"ledger":self.verify_ledger(),"db_integrity":self.conn.execute("PRAGMA integrity_check").fetchone()[0]}
    def bundle(self,out):
        out=Path(out)
        with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
            for table in ["credentials","policy_rules","policy_decisions","credential_history","findings","ledger"]:
                rows=[dict(r) for r in self.conn.execute(f"SELECT * FROM {table} ORDER BY 1")]
                z.writestr(f"{table}.json",json.dumps(rows,indent=2,default=str))
            z.writestr("manifest.json",json.dumps({"stats":self.stats(),"created":time.time()},indent=2))
        return {"bundle":str(out),"exists":out.exists()}

class PolicyEngine:
    def __init__(self,store): self.store=store
    def check(self,action,actor,cred=None,ctx=None):
        ctx=ctx or {}
        rules=[dict(r) for r in self.store.conn.execute("SELECT * FROM policy_rules WHERE action=? AND role=? ORDER BY priority DESC",(action,actor.role))]
        if not rules: return {"allowed":False,"reason":"no_matching_policy_rule"}
        last_fail=[]
        for rule in rules:
            cond=json.loads(rule["conditions_json"] or "{}")
            if not rule["allow"] and not cond:
                return {"allowed":False,"reason":rule["reason"],"rule_id":rule["rule_id"]}
            ok=True; fails=[]
            if "min_trust" in cond and actor.trust_score<cond["min_trust"]: ok=False; fails.append("trust")
            if "status" in cond and cred and cred["status"] not in cond["status"]: ok=False; fails.append("status")
            if cond.get("requires_finding") and not ctx.get("finding"): ok=False; fails.append("finding_required")
            if "window_days" in cond and cred:
                days=(cred["expires_ts"]-time.time())/86400
                if days>cond["window_days"]: ok=False; fails.append("renewal_window")
            if ok: return {"allowed":bool(rule["allow"]),"reason":rule["reason"],"rule_id":rule["rule_id"]}
            last_fail=fails
        return {"allowed":False,"reason":"policy_conditions_failed:"+",".join(last_fail or ["unknown"])}
class CredentialLifecycle:
    def __init__(self,store): self.store=store; self.policy=PolicyEngine(store)
    def issue(self,c,actor,reason="issue"):
        pol=self.policy.check("issue",actor)
        self.store.policy_decision(c.credential_id,"issue",actor,pol["allowed"],pol["reason"],pol)
        if not pol["allowed"]:
            self.store.conn.commit(); return {"ok":False,"denied":pol}
        fp=c.fingerprint()
        self.store.conn.execute("INSERT OR REPLACE INTO credentials VALUES(?,?,?,?,?,?,?,?,?)",(c.credential_id,c.subject_id,c.credential_type,"active",c.issued_ts,c.expires_ts,c.proof_hash,fp,time.time()))
        self.store.history(c.credential_id,"issue","none","active",actor,reason)
        self.store.conn.commit()
        return {"ok":True,"credential_id":c.credential_id,"status":"active","fingerprint":fp}
    def transition(self,cid,action,to_status,actor,reason="",ctx=None):
        cur=self.store.get(cid)
        if not cur: return {"ok":False,"reason":"missing_credential"}
        pol=self.policy.check(action,actor,cur,ctx or {})
        self.store.policy_decision(cid,action,actor,pol["allowed"],pol["reason"],pol)
        if not pol["allowed"]:
            self.store.conn.commit(); return {"ok":False,"denied":pol}
        if (cur["status"],to_status) in {("revoked","active"),("expired","active"),("replaced","active")}:
            self.store.finding(cid,"invalid_lifecycle_transition","high",{"from":cur["status"],"to":to_status})
            self.store.conn.commit()
            return {"ok":False,"reason":"invalid_transition"}
        self.store.conn.execute("UPDATE credentials SET status=?,updated_ts=? WHERE credential_id=?",(to_status,time.time(),cid))
        self.store.history(cid,action,cur["status"],to_status,actor,reason)
        self.store.conn.commit()
        return {"ok":True,"credential_id":cid,"from":cur["status"],"to":to_status}
    def suspend(self,cid,actor,reason="suspend"): return self.transition(cid,"suspend","suspended",actor,reason)
    def revoke(self,cid,actor,reason="revoke",finding=False): return self.transition(cid,"revoke","revoked",actor,reason,{"finding":finding})
    def renew(self,cid,new_id,actor,ttl_days=365,reason="renew"):
        cur=self.store.get(cid)
        if not cur: return {"ok":False,"reason":"missing_credential"}
        pol=self.policy.check("renew",actor,cur,{})
        self.store.policy_decision(cid,"renew",actor,pol["allowed"],pol["reason"],pol)
        if not pol["allowed"]:
            self.store.conn.commit(); return {"ok":False,"denied":pol}
        self.store.conn.execute("UPDATE credentials SET status=?,updated_ts=? WHERE credential_id=?",("replaced",time.time(),cid))
        self.store.history(cid,"renew",cur["status"],"replaced",actor,reason)
        new=Credential.create(new_id,cur["subject_id"],cur["credential_type"],ttl_days,cur["proof_hash"])
        fp=new.fingerprint()
        self.store.conn.execute("INSERT OR REPLACE INTO credentials VALUES(?,?,?,?,?,?,?,?,?)",(new.credential_id,new.subject_id,new.credential_type,"active",new.issued_ts,new.expires_ts,new.proof_hash,fp,time.time()))
        self.store.history(new_id,"issue","none","active",actor,reason)
        self.store.conn.commit()
        return {"ok":True,"old":cid,"new":new_id}
