
import json,hashlib,sqlite3,time,zipfile,re
from pathlib import Path
def digest(o): return hashlib.sha256(json.dumps(o,sort_keys=True,default=str).encode()).hexdigest()
class Templates:
    def __init__(self,path="templates.db",office="north"):
        self.office=office; self.conn=sqlite3.connect(Path(path)); self.conn.row_factory=sqlite3.Row
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS templates(id TEXT PRIMARY KEY,name TEXT,version INTEGER,status TEXT,fields TEXT,proofs TEXT,rules TEXT,hash TEXT);
        CREATE TABLE IF NOT EXISTS validations(id INTEGER PRIMARY KEY,ts REAL,template TEXT,subject TEXT,result TEXT,details TEXT);
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,ts REAL,type TEXT,subject TEXT,details TEXT);
        CREATE TABLE IF NOT EXISTS ledger(seq INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT,subject TEXT,payload_hash TEXT,prev_hash TEXT,entry_hash TEXT);
        """); self.conn.commit()
    def last_hash(self):
        r=self.conn.execute("SELECT entry_hash FROM ledger ORDER BY seq DESC LIMIT 1").fetchone()
        return r["entry_hash"] if r else "GENESIS"
    def receipt(self,k,s,p):
        prev=self.last_hash(); ph=digest(p); eh=digest({"kind":k,"subject":s,"payload_hash":ph,"prev_hash":prev})
        self.conn.execute("INSERT INTO ledger(kind,subject,payload_hash,prev_hash,entry_hash) VALUES(?,?,?,?,?)",(k,s,ph,prev,eh)); self.conn.commit()
    def event(self,t,s,d=None):
        self.conn.execute("INSERT INTO events(ts,type,subject,details) VALUES(?,?,?,?)",(time.time(),t,s,json.dumps(d or {},default=str)))
        self.receipt("event",s,{"type":t,"details":d or {}})
    def verify_ledger(self):
        prev="GENESIS"; n=0
        for r in self.conn.execute("SELECT seq,kind,subject,payload_hash,prev_hash,entry_hash FROM ledger ORDER BY seq"):
            exp=digest({"kind":r["kind"],"subject":r["subject"],"payload_hash":r["payload_hash"],"prev_hash":prev})
            if r["prev_hash"]!=prev: return {"ok":False,"seq":r["seq"],"reason":"prev_hash_mismatch"}
            if r["entry_hash"]!=exp: return {"ok":False,"seq":r["seq"],"reason":"entry_hash_mismatch"}
            prev=r["entry_hash"]; n+=1
        return {"ok":True,"entries":n,"head":prev}
    def tid(self,name,version): return "template:"+digest({"name":name,"version":version})[:16]
    def create(self,name,fields,proofs=None,rules=None,version=1):
        tid=self.tid(name,version); payload={"name":name,"version":version,"fields":fields,"proofs":proofs or [],"rules":rules or {}}
        h=digest(payload)
        self.conn.execute("INSERT OR REPLACE INTO templates VALUES(?,?,?,?,?,?,?,?)",(tid,name,version,"active",json.dumps(fields),json.dumps(proofs or []),json.dumps(rules or {}),h))
        self.event("template_created",tid,{"name":name,"version":version,"hash":h}); self.conn.commit()
        return {"template":tid,"name":name,"version":version,"hash":h}
    def get(self,tid):
        r=self.conn.execute("SELECT * FROM templates WHERE id=?",(tid,)).fetchone()
        return dict(r) if r else None
    def list(self): return [dict(r) for r in self.conn.execute("SELECT id,name,version,status,hash FROM templates ORDER BY name,version")]
    def check_field(self,n,spec,val):
        if spec.get("required") and (val is None or val==""): return f"{n}:missing"
        if val is None: return None
        if spec.get("type")=="number" and not isinstance(val,(int,float)): return f"{n}:not_number"
        if spec.get("type")=="date" and not re.match(r"^\d{4}-\d{2}-\d{2}$",str(val)): return f"{n}:bad_date"
        if "enum" in spec and val not in spec["enum"]: return f"{n}:not_allowed"
        return None
    def validate(self,tid,subject,claim,provided=None):
        tpl=self.get(tid)
        if not tpl: return {"ok":False,"reason":"missing_template"}
        fields=json.loads(tpl["fields"]); proofs=json.loads(tpl["proofs"]); rules=json.loads(tpl["rules"])
        errors=[]
        for f,spec in fields.items():
            e=self.check_field(f,spec,claim.get(f))
            if e: errors.append(e)
        have=set(provided or [])
        for p in proofs:
            if p not in have: errors.append("proof_missing:"+p)
        if "min_trust" in rules and float(claim.get("trust_score",0))<float(rules["min_trust"]): errors.append("trust_below_minimum")
        result="pass" if not errors else "fail"
        self.conn.execute("INSERT INTO validations(ts,template,subject,result,details) VALUES(?,?,?,?,?)",(time.time(),tid,subject,result,json.dumps({"errors":errors,"claim":claim,"proofs":provided or []},default=str)))
        self.event("template_validation",tid,{"subject":subject,"result":result,"errors":errors}); self.conn.commit()
        return {"ok":not errors,"template":tid,"subject":subject,"errors":errors}
    def derive(self,tid,subject,claim,proofs):
        v=self.validate(tid,subject,claim,proofs)
        if not v["ok"]: return {"ok":False,"validation":v}
        cid="credential:"+digest({"template":tid,"subject":subject,"claim":claim,"ts":time.time()})[:16]
        cred={"credential":cid,"template":tid,"subject":subject,"claim":claim,"proofs":proofs,"issuer":self.office,"status":"ready","hash":digest({"template":tid,"subject":subject,"claim":claim})}
        self.event("credential_derived",cid,cred); return {"ok":True,"credential":cred}
    def requirements(self,tid):
        tpl=self.get(tid)
        if not tpl: return {"ok":False,"reason":"missing_template"}
        return {"template":tid,"fields":json.loads(tpl["fields"]),"proofs":json.loads(tpl["proofs"]),"rules":json.loads(tpl["rules"])}
    def stats(self):
        return {"office":self.office,"templates":self.conn.execute("SELECT COUNT(*) n FROM templates").fetchone()["n"],"validations":self.conn.execute("SELECT COUNT(*) n FROM validations").fetchone()["n"],"events":self.conn.execute("SELECT COUNT(*) n FROM events").fetchone()["n"],"ledger":self.verify_ledger(),"db_integrity":self.conn.execute("PRAGMA integrity_check").fetchone()[0]}
    def bundle(self,out):
        out=Path(out)
        with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
            for t in ["templates","validations","events","ledger"]:
                z.writestr(f"{t}.json",json.dumps([dict(r) for r in self.conn.execute(f"SELECT * FROM {t} ORDER BY 1")],indent=2,default=str))
            z.writestr("manifest.json",json.dumps({"stats":self.stats(),"created":time.time()},indent=2))
        return {"bundle":str(out),"exists":out.exists()}
def seed_demo(e):
    lic=e.create("driver_license",{"full_name":{"type":"string","required":True},"dob":{"type":"date","required":True},"state":{"type":"string","required":True,"enum":["MN","WI","IA","ND"]},"class":{"type":"string","required":True,"enum":["D","M","CDL"]},"trust_score":{"type":"number","required":True}},["identity_proof","address_proof"],{"min_trust":60})
    sid=e.create("state_id",{"full_name":{"type":"string","required":True},"dob":{"type":"date","required":True},"state":{"type":"string","required":True},"trust_score":{"type":"number","required":True}},["identity_proof"],{"min_trust":50})
    good=e.derive(lic["template"],"citizen:root",{"full_name":"Root User","dob":"1981-06-21","state":"MN","class":"D","trust_score":88},["identity_proof","address_proof"])
    bad=e.derive(lic["template"],"citizen:weak",{"full_name":"Weak","dob":"bad","state":"XX","class":"D","trust_score":20},["identity_proof"])
    return {"license":lic,"state_id":sid,"good":good,"bad":bad}
