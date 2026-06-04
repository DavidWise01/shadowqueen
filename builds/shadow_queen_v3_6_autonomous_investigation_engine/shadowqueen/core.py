
import json,hashlib,sqlite3,time,zipfile
from pathlib import Path
def digest(o): return hashlib.sha256(json.dumps(o,sort_keys=True,default=str).encode()).hexdigest()
class InvestigationEngine:
    def __init__(self,path="investigations.db",domain="shadow-investigations"):
        self.domain=domain; self.conn=sqlite3.connect(Path(path)); self.conn.row_factory=sqlite3.Row
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS cases(id TEXT PRIMARY KEY,subject TEXT,kind TEXT,severity TEXT,status TEXT,score REAL,assigned TEXT,details TEXT);
        CREATE TABLE IF NOT EXISTS evidence(id TEXT PRIMARY KEY,case_id TEXT,source TEXT,kind TEXT,weight REAL,hash TEXT,details TEXT);
        CREATE TABLE IF NOT EXISTS triage(id INTEGER PRIMARY KEY,case_id TEXT,result TEXT,score REAL,reasons TEXT,action TEXT);
        CREATE TABLE IF NOT EXISTS actions(id INTEGER PRIMARY KEY,case_id TEXT,action TEXT,status TEXT,actor TEXT,details TEXT);
        CREATE TABLE IF NOT EXISTS rules(id TEXT PRIMARY KEY,condition TEXT,weight REAL,action TEXT,severity TEXT);
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,type TEXT,subject TEXT,details TEXT);
        CREATE TABLE IF NOT EXISTS ledger(seq INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT,subject TEXT,payload_hash TEXT,prev_hash TEXT,entry_hash TEXT);
        """); self.conn.commit(); self.seed_rules()
    def seed_rules(self):
        rules=[
            ("duplicate_identity","possible_duplicate_identity",35,"escalate_identity_review","high"),
            ("synthetic_identity","synthetic_identity_signal",45,"quarantine_identity","critical"),
            ("credential_stuffing","credential_stuffing_signal",40,"suspend_credential_review","high"),
            ("address_cluster","suspicious_address_cluster",30,"field_verification","high"),
            ("office_drift","credential_status_disagreement",35,"route_to_federation_ops","high"),
            ("revocation","revoked_credential_presented",50,"block_presentation","critical")]
        for r in rules: self.conn.execute("INSERT OR IGNORE INTO rules VALUES(?,?,?,?,?)",r)
        self.conn.commit()
    def last_hash(self):
        r=self.conn.execute("SELECT entry_hash FROM ledger ORDER BY seq DESC LIMIT 1").fetchone()
        return r["entry_hash"] if r else "GENESIS"
    def receipt(self,k,s,p):
        prev=self.last_hash(); ph=digest(p); eh=digest({"kind":k,"subject":s,"payload_hash":ph,"prev_hash":prev})
        self.conn.execute("INSERT INTO ledger(kind,subject,payload_hash,prev_hash,entry_hash) VALUES(?,?,?,?,?)",(k,s,ph,prev,eh)); self.conn.commit()
    def event(self,t,s,d=None):
        self.conn.execute("INSERT INTO events(type,subject,details) VALUES(?,?,?)",(t,s,json.dumps(d or {},default=str)))
        self.receipt("event",s,{"type":t,"details":d or {}})
    def verify_ledger(self):
        prev="GENESIS"; n=0
        for r in self.conn.execute("SELECT seq,kind,subject,payload_hash,prev_hash,entry_hash FROM ledger ORDER BY seq"):
            exp=digest({"kind":r["kind"],"subject":r["subject"],"payload_hash":r["payload_hash"],"prev_hash":prev})
            if r["prev_hash"]!=prev: return {"ok":False,"seq":r["seq"],"reason":"prev_hash_mismatch"}
            if r["entry_hash"]!=exp: return {"ok":False,"seq":r["seq"],"reason":"entry_hash_mismatch"}
            prev=r["entry_hash"]; n+=1
        return {"ok":True,"entries":n,"head":prev}
    def open_case(self,subject,kind,severity="medium",details=None,assigned="auto"):
        cid="case:"+digest({"subject":subject,"kind":kind,"t":time.time()})[:16]
        self.conn.execute("INSERT INTO cases VALUES(?,?,?,?,?,?,?,?)",(cid,subject,kind,severity,"open",0.0,assigned,json.dumps(details or {},default=str)))
        self.event("case_opened",cid,{"subject":subject,"kind":kind,"severity":severity}); self.conn.commit()
        return {"case":cid,"status":"open","severity":severity}
    def add_evidence(self,cid,source,kind,weight=10,details=None):
        payload={"case":cid,"source":source,"kind":kind,"weight":weight,"details":details or {}}
        h=digest(payload); eid="evidence:"+h[:16]
        self.conn.execute("INSERT OR REPLACE INTO evidence VALUES(?,?,?,?,?,?,?)",(eid,cid,source,kind,float(weight),h,json.dumps(details or {},default=str)))
        self.event("evidence_added",cid,{"evidence":eid,"kind":kind,"weight":weight}); self.conn.commit()
        return {"evidence":eid,"hash":h}
    def triage_case(self,cid):
        ev=[dict(r) for r in self.conn.execute("SELECT * FROM evidence WHERE case_id=?",(cid,))]
        score=0.0; reasons=[]; action="monitor"
        for e in ev:
            score+=float(e["weight"]); reasons.append({"kind":e["kind"],"weight":e["weight"]})
            for r in self.conn.execute("SELECT * FROM rules WHERE condition=?",(e["kind"],)):
                score+=float(r["weight"]); action=r["action"]; reasons.append({"rule":r["id"],"weight":r["weight"],"action":r["action"]})
        result="critical" if score>=90 else "high" if score>=60 else "medium" if score>=30 else "low"
        self.conn.execute("INSERT INTO triage(case_id,result,score,reasons,action) VALUES(?,?,?,?,?)",(cid,result,score,json.dumps(reasons,default=str),action))
        self.conn.execute("UPDATE cases SET score=?,severity=? WHERE id=?",(score,result,cid))
        self.event("case_triaged",cid,{"result":result,"score":score,"action":action}); self.conn.commit()
        return {"case":cid,"result":result,"score":score,"recommended_action":action}
    def execute(self,cid,actor="auto"):
        t=self.conn.execute("SELECT * FROM triage WHERE case_id=? ORDER BY id DESC LIMIT 1",(cid,)).fetchone()
        if not t: return {"ok":False,"reason":"missing_triage"}
        status="executed" if t["result"] in ("high","critical") else "queued"
        self.conn.execute("INSERT INTO actions(case_id,action,status,actor,details) VALUES(?,?,?,?,?)",(cid,t["action"],status,actor,json.dumps({"score":t["score"],"result":t["result"]})))
        self.conn.execute("UPDATE cases SET status=? WHERE id=?",("contained" if t["action"].startswith(("quarantine","block")) else "actioned",cid))
        self.event("recommendation_executed",cid,{"action":t["action"],"status":status}); self.conn.commit()
        return {"case":cid,"action":t["action"],"status":status}
    def ingest(self,subject,kind,severity="medium",score=50,details=None):
        c=self.open_case(subject,kind,severity,details); self.add_evidence(c["case"],"signal",kind,score,details or {})
        t=self.triage_case(c["case"]); a=self.execute(c["case"]); return {"case":c,"triage":t,"action":a}
    def cases(self): return [dict(r) for r in self.conn.execute("SELECT * FROM cases ORDER BY id")]
    def actions(self): return [dict(r) for r in self.conn.execute("SELECT * FROM actions ORDER BY id")]
    def dashboard(self):
        cs=self.cases()
        return {"domain":self.domain,"cases":len(cs),"open":len([c for c in cs if c["status"]=="open"]),"actioned":len([c for c in cs if c["status"]=="actioned"]),"contained":len([c for c in cs if c["status"]=="contained"]),"critical":len([c for c in cs if c["severity"]=="critical"]),"high":len([c for c in cs if c["severity"]=="high"]),"ledger":self.verify_ledger()}
    def stats(self):
        return {"domain":self.domain,"cases":self.conn.execute("SELECT COUNT(*) n FROM cases").fetchone()["n"],"evidence":self.conn.execute("SELECT COUNT(*) n FROM evidence").fetchone()["n"],"triage":self.conn.execute("SELECT COUNT(*) n FROM triage").fetchone()["n"],"actions":self.conn.execute("SELECT COUNT(*) n FROM actions").fetchone()["n"],"rules":self.conn.execute("SELECT COUNT(*) n FROM rules").fetchone()["n"],"events":self.conn.execute("SELECT COUNT(*) n FROM events").fetchone()["n"],"ledger":self.verify_ledger(),"db_integrity":self.conn.execute("PRAGMA integrity_check").fetchone()[0]}
    def bundle(self,out):
        out=Path(out)
        with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
            for t in ["cases","evidence","triage","actions","rules","events","ledger"]:
                z.writestr(f"{t}.json",json.dumps([dict(r) for r in self.conn.execute(f"SELECT * FROM {t} ORDER BY 1")],indent=2,default=str))
            z.writestr("dashboard.json",json.dumps(self.dashboard(),indent=2,default=str))
            z.writestr("manifest.json",json.dumps({"stats":self.stats(),"created":time.time()},indent=2))
        return {"bundle":str(out),"exists":out.exists()}
def seed_demo(e):
    a=e.ingest("person:synthetic","synthetic_identity_signal","high",70,{"source":"fraud"})
    b=e.ingest("credential:C-1","credential_stuffing_signal","medium",45,{"count":5})
    c=e.ingest("office:east","credential_status_disagreement","high",40,{"north":"active","east":"revoked"})
    return {"synthetic":a,"stuffing":b,"federation":c,"dashboard":e.dashboard()}
