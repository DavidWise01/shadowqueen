
import json,hashlib,sqlite3,time,zipfile
from pathlib import Path
from dataclasses import dataclass,field

def digest(o): return hashlib.sha256(json.dumps(o,sort_keys=True,default=str).encode()).hexdigest()

@dataclass(frozen=True)
class PolicyRule:
    rule_id:str; action:str; role:str; allow:bool; conditions:dict=field(default_factory=dict); reason:str=""; priority:int=100; version:int=1; office_id:str="local"
    @classmethod
    def from_dict(cls,d,office=None):
        return cls(str(d["rule_id"]),str(d["action"]),str(d["role"]),bool(d["allow"]),dict(d.get("conditions",{})),str(d.get("reason","")),int(d.get("priority",100)),int(d.get("version",1)),str(office or d.get("office_id","local")))
    def canonical(self):
        return {"rule_id":self.rule_id,"action":self.action,"role":self.role,"allow":self.allow,"conditions":self.conditions,"reason":self.reason,"priority":self.priority,"version":self.version}
    def hash(self): return digest(self.canonical())

class Store:
    def __init__(self,path="policy_federation.db",office_id="north"):
        self.office_id=office_id
        self.conn=sqlite3.connect(Path(path)); self.conn.row_factory=sqlite3.Row
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS rules(rule_id TEXT,office_id TEXT,action TEXT,role TEXT,allow INTEGER,conditions_json TEXT,reason TEXT,priority INTEGER,version INTEGER,rule_hash TEXT,PRIMARY KEY(rule_id,office_id));
        CREATE TABLE IF NOT EXISTS bundles(office_id TEXT PRIMARY KEY,version INTEGER,policy_hash TEXT,bundle_json TEXT,ts REAL);
        CREATE TABLE IF NOT EXISTS conflicts(id INTEGER PRIMARY KEY,ts REAL,rule_id TEXT,local_office TEXT,remote_office TEXT,kind TEXT,severity TEXT,status TEXT,details_json TEXT);
        CREATE TABLE IF NOT EXISTS overrides(id INTEGER PRIMARY KEY,ts REAL,rule_id TEXT,from_office TEXT,to_office TEXT,action TEXT,actor TEXT,reason TEXT);
        CREATE TABLE IF NOT EXISTS audits(id INTEGER PRIMARY KEY,ts REAL,auditor TEXT,result TEXT,details_json TEXT);
        CREATE TABLE IF NOT EXISTS ledger(seq INTEGER PRIMARY KEY AUTOINCREMENT,ts REAL,kind TEXT,subject TEXT,payload_hash TEXT,prev_hash TEXT,entry_hash TEXT);
        """); self.conn.commit(); self.seed()
    def seed(self):
        if self.conn.execute("SELECT COUNT(*) n FROM rules WHERE office_id=?",(self.office_id,)).fetchone()["n"]: return
        for r in [
            PolicyRule("issue.registrar","issue","registrar",True,{"min_trust":0.6},"registrar may issue",100,1,self.office_id),
            PolicyRule("issue.clerk.deny","issue","clerk",False,{},"clerk cannot issue",100,1,self.office_id),
            PolicyRule("renew.registrar","renew","registrar",True,{"status":["active","suspended"],"window_days":90},"renew in window",100,1,self.office_id),
            PolicyRule("revoke.auditor","revoke","auditor",True,{"status":["suspended"],"requires_finding":1},"auditor revoke",100,1,self.office_id),
            PolicyRule("revoke.clerk.deny","revoke","clerk",False,{},"clerk cannot revoke",100,1,self.office_id)]:
            self.upsert(r,False)
        self.conn.commit()
    def last_hash(self):
        r=self.conn.execute("SELECT entry_hash FROM ledger ORDER BY seq DESC LIMIT 1").fetchone()
        return r["entry_hash"] if r else "GENESIS"
    def receipt(self,k,s,p):
        prev=self.last_hash(); ph=digest(p); eh=digest({"kind":k,"subject":s,"payload_hash":ph,"prev_hash":prev})
        self.conn.execute("INSERT INTO ledger(ts,kind,subject,payload_hash,prev_hash,entry_hash) VALUES(?,?,?,?,?,?)",(time.time(),k,s,ph,prev,eh)); self.conn.commit()
    def verify_ledger(self):
        prev="GENESIS"; n=0
        for r in self.conn.execute("SELECT seq,kind,subject,payload_hash,prev_hash,entry_hash FROM ledger ORDER BY seq"):
            exp=digest({"kind":r["kind"],"subject":r["subject"],"payload_hash":r["payload_hash"],"prev_hash":prev})
            if r["prev_hash"]!=prev: return {"ok":False,"seq":r["seq"],"reason":"prev_hash_mismatch"}
            if r["entry_hash"]!=exp: return {"ok":False,"seq":r["seq"],"reason":"entry_hash_mismatch"}
            prev=r["entry_hash"]; n+=1
        return {"ok":True,"entries":n,"head":prev}
    def upsert(self,r,rec=True):
        self.conn.execute("INSERT OR REPLACE INTO rules VALUES(?,?,?,?,?,?,?,?,?,?)",(r.rule_id,r.office_id,r.action,r.role,1 if r.allow else 0,json.dumps(r.conditions),r.reason,r.priority,r.version,r.hash()))
        if rec: self.receipt("rule",f"{r.office_id}:{r.rule_id}",r.canonical())
    def rules(self,office=None):
        rows=self.conn.execute("SELECT * FROM rules WHERE office_id=? ORDER BY rule_id",(office or self.office_id,))
        return [PolicyRule(x["rule_id"],x["action"],x["role"],bool(x["allow"]),json.loads(x["conditions_json"] or "{}"),x["reason"],x["priority"],x["version"],x["office_id"]) for x in rows]
    def export_bundle(self):
        rules=self.rules(self.office_id); data={"office_id":self.office_id,"version":max([r.version for r in rules] or [1]),"rules":[r.canonical() for r in rules]}
        data["policy_hash"]=digest(data)
        self.conn.execute("INSERT OR REPLACE INTO bundles VALUES(?,?,?,?,?)",(self.office_id,data["version"],data["policy_hash"],json.dumps(data),time.time()))
        self.receipt("bundle_export",self.office_id,data); self.conn.commit(); return data
    def import_bundle(self,data):
        office=data["office_id"]
        self.conn.execute("INSERT OR REPLACE INTO bundles VALUES(?,?,?,?,?)",(office,int(data.get("version",1)),data.get("policy_hash",digest(data)),json.dumps(data),time.time()))
        for rd in data.get("rules",[]): self.upsert(PolicyRule.from_dict(rd,office),False)
        self.receipt("bundle_import",office,data); self.conn.commit()
        return self.compare(office)
    def conflict(self,rule_id,remote,kind,severity,details):
        self.conn.execute("INSERT INTO conflicts(ts,rule_id,local_office,remote_office,kind,severity,status,details_json) VALUES(?,?,?,?,?,?,?,?)",(time.time(),rule_id,self.office_id,remote,kind,severity,"open",json.dumps(details,default=str)))
        self.receipt("conflict",rule_id,{"remote":remote,"kind":kind,"severity":severity})
    def compare(self,remote):
        local={r.rule_id:r for r in self.rules(self.office_id)}; out=[]
        for rr in self.rules(remote):
            lr=local.get(rr.rule_id)
            if not lr:
                c={"rule_id":rr.rule_id,"kind":"missing_local_rule"}; self.conflict(rr.rule_id,remote,"missing_local_rule","medium",c); out.append(c)
            elif lr.allow != rr.allow:
                c={"rule_id":rr.rule_id,"kind":"allow_deny_mismatch","local":lr.canonical(),"remote":rr.canonical()}; self.conflict(rr.rule_id,remote,"allow_deny_mismatch","high",c); out.append(c)
            elif lr.hash()!=rr.hash():
                c={"rule_id":rr.rule_id,"kind":"rule_drift","local_hash":lr.hash(),"remote_hash":rr.hash(),"local_version":lr.version,"remote_version":rr.version}; self.conflict(rr.rule_id,remote,"rule_drift","high" if rr.version>lr.version else "medium",c); out.append(c)
        return {"remote_office":remote,"conflict_count":len(out),"conflicts":out}
    def override(self,rule_id,remote,action,actor="queen",reason="override"):
        self.conn.execute("INSERT INTO overrides(ts,rule_id,from_office,to_office,action,actor,reason) VALUES(?,?,?,?,?,?,?)",(time.time(),rule_id,remote,self.office_id,action,actor,reason))
        if action=="accept_remote":
            row=self.conn.execute("SELECT * FROM rules WHERE rule_id=? AND office_id=?",(rule_id,remote)).fetchone()
            if row:
                self.upsert(PolicyRule(row["rule_id"],row["action"],row["role"],bool(row["allow"]),json.loads(row["conditions_json"] or "{}"),row["reason"],row["priority"],row["version"],self.office_id),False)
                self.conn.execute("UPDATE conflicts SET status='resolved' WHERE rule_id=? AND remote_office=?",(rule_id,remote))
        self.receipt("override",rule_id,{"remote":remote,"action":action,"actor":actor,"reason":reason}); self.conn.commit()
        return {"ok":True,"rule_id":rule_id,"action":action}
    def audit(self,auditor="auditor"):
        open_conf=self.conn.execute("SELECT COUNT(*) n FROM conflicts WHERE status='open'").fetchone()["n"]
        result="pass" if open_conf==0 else "warning"
        details={"open_conflicts":open_conf,"local_hash":self.export_bundle()["policy_hash"]}
        self.conn.execute("INSERT INTO audits(ts,auditor,result,details_json) VALUES(?,?,?,?)",(time.time(),auditor,result,json.dumps(details)))
        self.receipt("audit",auditor,{"result":result,"details":details}); self.conn.commit()
        return {"auditor":auditor,"result":result,"details":details}
    def list_rules(self):
        return [dict(r) for r in self.conn.execute("SELECT rule_id,office_id,action,role,allow,conditions_json,version,rule_hash FROM rules ORDER BY office_id,rule_id")]
    def conflicts(self):
        return [dict(r) for r in self.conn.execute("SELECT rule_id,remote_office,kind,severity,status,details_json FROM conflicts ORDER BY id")]
    def stats(self):
        return {"office_id":self.office_id,"rules":self.conn.execute("SELECT COUNT(*) n FROM rules").fetchone()["n"],"bundles":self.conn.execute("SELECT COUNT(*) n FROM bundles").fetchone()["n"],"conflicts":self.conn.execute("SELECT COUNT(*) n FROM conflicts").fetchone()["n"],"overrides":self.conn.execute("SELECT COUNT(*) n FROM overrides").fetchone()["n"],"audits":self.conn.execute("SELECT COUNT(*) n FROM audits").fetchone()["n"],"ledger":self.verify_ledger(),"db_integrity":self.conn.execute("PRAGMA integrity_check").fetchone()[0]}
    def bundle_zip(self,out):
        out=Path(out)
        with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
            for t in ["rules","bundles","conflicts","overrides","audits","ledger"]:
                rows=[dict(r) for r in self.conn.execute(f"SELECT * FROM {t} ORDER BY 1")]
                z.writestr(f"{t}.json",json.dumps(rows,indent=2,default=str))
            z.writestr("manifest.json",json.dumps({"stats":self.stats(),"created":time.time()},indent=2))
        return {"bundle":str(out),"exists":out.exists()}
