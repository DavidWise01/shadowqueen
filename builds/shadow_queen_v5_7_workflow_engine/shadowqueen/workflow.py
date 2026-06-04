
import json,sqlite3,time,hashlib,zipfile
from pathlib import Path
def digest(o): return hashlib.sha256(json.dumps(o,sort_keys=True,default=str).encode()).hexdigest()
class WorkflowEngine:
    def __init__(self,path="workflow.db",office="office:north"):
        self.office=office; self.conn=sqlite3.connect(Path(path)); self.conn.row_factory=sqlite3.Row
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS defs(id TEXT PRIMARY KEY,name TEXT,states TEXT,transitions TEXT,status TEXT);
        CREATE TABLE IF NOT EXISTS flows(id TEXT PRIMARY KEY,def_id TEXT,subject TEXT,state TEXT,status TEXT,owner TEXT,context TEXT);
        CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY,flow TEXT,kind TEXT,assignee TEXT,status TEXT,details TEXT);
        CREATE TABLE IF NOT EXISTS decisions(id INTEGER PRIMARY KEY,flow TEXT,actor TEXT,decision TEXT,from_state TEXT,to_state TEXT,details TEXT);
        CREATE TABLE IF NOT EXISTS citizen(subject TEXT PRIMARY KEY,status TEXT,active INTEGER,flags TEXT);
        CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,actor TEXT,action TEXT,subject TEXT,result TEXT,details TEXT);
        CREATE TABLE IF NOT EXISTS ledger(seq INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT,subject TEXT,payload_hash TEXT,prev_hash TEXT,entry_hash TEXT);
        """); self.conn.commit(); self.seed_defs()
    def last_hash(self):
        r=self.conn.execute("SELECT entry_hash FROM ledger ORDER BY seq DESC LIMIT 1").fetchone()
        return r["entry_hash"] if r else "GENESIS"
    def receipt(self,k,s,p):
        prev=self.last_hash(); ph=digest(p); eh=digest({"kind":k,"subject":s,"payload_hash":ph,"prev_hash":prev})
        self.conn.execute("INSERT INTO ledger(kind,subject,payload_hash,prev_hash,entry_hash) VALUES(?,?,?,?,?)",(k,s,ph,prev,eh)); self.conn.commit()
    def verify_ledger(self):
        prev="GENESIS"; n=0
        for r in self.conn.execute("SELECT * FROM ledger ORDER BY seq"):
            exp=digest({"kind":r["kind"],"subject":r["subject"],"payload_hash":r["payload_hash"],"prev_hash":prev})
            if r["prev_hash"]!=prev: return {"ok":False,"seq":r["seq"],"reason":"prev_hash_mismatch"}
            if r["entry_hash"]!=exp: return {"ok":False,"seq":r["seq"],"reason":"entry_hash_mismatch"}
            prev=r["entry_hash"]; n+=1
        return {"ok":True,"entries":n,"head":prev}
    def audit_log(self,actor,action,subject,result="ok",details=None):
        self.conn.execute("INSERT INTO audit(actor,action,subject,result,details) VALUES(?,?,?,?,?)",(actor,action,subject,result,json.dumps(details or {})))
        self.receipt("audit",subject,{"actor":actor,"action":action,"result":result})
    def define(self,name,states,transitions):
        did="wfdef:"+digest(name)[:16]
        self.conn.execute("INSERT OR REPLACE INTO defs VALUES(?,?,?,?,?)",(did,name,json.dumps(states),json.dumps(transitions),"active"))
        self.audit_log(self.office,"define",did,"ok",{"name":name})
    def seed_defs(self):
        if self.conn.execute("SELECT COUNT(*) n FROM defs").fetchone()["n"]: return
        self.define("credential_renewal",["submitted","identity_check","fee_check","operator_review","approved","denied","issued"],{"submitted":["identity_check"],"identity_check":["fee_check","denied"],"fee_check":["operator_review","denied"],"operator_review":["approved","denied"],"approved":["issued"],"denied":[],"issued":[]})
        self.define("credential_transfer",["submitted","ownership_check","office_review","approved","denied","transferred"],{"submitted":["ownership_check"],"ownership_check":["office_review","denied"],"office_review":["approved","denied"],"approved":["transferred"],"denied":[],"transferred":[]})
        self.define("suspension",["opened","evidence_review","notice_sent","hearing","suspended","dismissed","appealed"],{"opened":["evidence_review"],"evidence_review":["notice_sent","dismissed"],"notice_sent":["hearing"],"hearing":["suspended","dismissed","appealed"],"suspended":["appealed"],"dismissed":[],"appealed":[]})
        self.define("appeal",["submitted","record_review","hearing_scheduled","decision_pending","granted","denied"],{"submitted":["record_review"],"record_review":["hearing_scheduled","denied"],"hearing_scheduled":["decision_pending"],"decision_pending":["granted","denied"],"granted":[],"denied":[]})
        self.define("case_review",["opened","triage","investigation","operator_decision","resolved","escalated"],{"opened":["triage"],"triage":["investigation","resolved"],"investigation":["operator_decision","escalated"],"operator_decision":["resolved","escalated"],"resolved":[],"escalated":[]})
    def def_by_name(self,name):
        r=self.conn.execute("SELECT * FROM defs WHERE name=?",(name,)).fetchone()
        return dict(r) if r else None
    def task(self,wid,kind,assignee,details=None):
        tid="task:"+digest({"wid":wid,"kind":kind,"t":time.time()})[:16]
        self.conn.execute("INSERT INTO tasks VALUES(?,?,?,?,?,?)",(tid,wid,kind,assignee,"open",json.dumps(details or {})))
        self.receipt("task",tid,{"workflow":wid})
    def open(self,name,subject,context=None,owner=None):
        d=self.def_by_name(name); states=json.loads(d["states"]); first=states[0]
        wid="workflow:"+digest({"name":name,"subject":subject,"t":time.time()})[:16]
        self.conn.execute("INSERT INTO flows VALUES(?,?,?,?,?,?,?)",(wid,d["id"],subject,first,"open",owner or self.office,json.dumps(context or {})))
        self.task(wid,"review",owner or self.office,{"state":first})
        self.update_citizen(subject)
        self.audit_log(owner or self.office,"open_workflow",wid,"ok",{"name":name})
        self.conn.commit(); return {"workflow":wid,"name":name,"subject":subject,"state":first}
    def flow(self,wid):
        r=self.conn.execute("SELECT * FROM flows WHERE id=?",(wid,)).fetchone()
        return dict(r) if r else None
    def allowed(self,wf,to_state):
        d=self.conn.execute("SELECT * FROM defs WHERE id=?",(wf["def_id"],)).fetchone()
        return to_state in json.loads(d["transitions"]).get(wf["state"],[])
    def decide(self,wid,actor,decision,to_state,details=None):
        wf=self.flow(wid)
        if not wf: return {"ok":False,"reason":"missing"}
        if not self.allowed(wf,to_state):
            self.conn.execute("INSERT INTO decisions(flow,actor,decision,from_state,to_state,details) VALUES(?,?,?,?,?,?)",(wid,actor,decision,wf["state"],to_state,json.dumps({"error":"invalid"})))
            self.audit_log(actor,"decision",wid,"denied",{"from":wf["state"],"to":to_state})
            self.conn.commit(); return {"ok":False,"reason":"invalid_transition","from":wf["state"],"to":to_state}
        terminal=("issued","denied","transferred","suspended","dismissed","granted","resolved","escalated")
        status="closed" if to_state in terminal else "open"
        self.conn.execute("UPDATE flows SET state=?,status=? WHERE id=?",(to_state,status,wid))
        self.conn.execute("UPDATE tasks SET status='closed' WHERE flow=? AND status='open'",(wid,))
        if status=="open": self.task(wid,"review",actor,{"state":to_state})
        self.conn.execute("INSERT INTO decisions(flow,actor,decision,from_state,to_state,details) VALUES(?,?,?,?,?,?)",(wid,actor,decision,wf["state"],to_state,json.dumps(details or {})))
        self.update_citizen(wf["subject"])
        self.audit_log(actor,"decision",wid,"ok",{"from":wf["state"],"to":to_state})
        self.conn.commit(); return {"ok":True,"workflow":wid,"from":wf["state"],"to":to_state,"status":status}
    def auto(self,wid,actor="auto"):
        wf=self.flow(wid); d=self.conn.execute("SELECT * FROM defs WHERE id=?",(wf["def_id"],)).fetchone()
        opts=json.loads(d["transitions"]).get(wf["state"],[])
        if not opts: return {"ok":False,"reason":"terminal"}
        preferred=[x for x in opts if x not in ("denied","dismissed","escalated","appealed")]
        return self.decide(wid,actor,"auto",(preferred or opts)[0],{})
    def update_citizen(self,subject):
        active=self.conn.execute("SELECT COUNT(*) n FROM flows WHERE subject=? AND status='open'",(subject,)).fetchone()["n"]
        flags=[r["state"] for r in self.conn.execute("SELECT state FROM flows WHERE subject=? AND status='open'",(subject,)) if r["state"] in ("hearing","operator_review","evidence_review")]
        self.conn.execute("INSERT OR REPLACE INTO citizen VALUES(?,?,?,?)",(subject,"active" if active else "clear",active,json.dumps(flags)))
        self.receipt("citizen",subject,{"active":active,"flags":flags})
    def queue(self): return [dict(r) for r in self.conn.execute("SELECT * FROM tasks WHERE status='open' ORDER BY id")]
    def stats(self):
        return {"office":self.office,"defs":self.conn.execute("SELECT COUNT(*) n FROM defs").fetchone()["n"],"workflows":self.conn.execute("SELECT COUNT(*) n FROM flows").fetchone()["n"],"open_workflows":self.conn.execute("SELECT COUNT(*) n FROM flows WHERE status='open'").fetchone()["n"],"tasks":self.conn.execute("SELECT COUNT(*) n FROM tasks").fetchone()["n"],"open_tasks":self.conn.execute("SELECT COUNT(*) n FROM tasks WHERE status='open'").fetchone()["n"],"decisions":self.conn.execute("SELECT COUNT(*) n FROM decisions").fetchone()["n"],"citizens":self.conn.execute("SELECT COUNT(*) n FROM citizen").fetchone()["n"],"ledger":self.verify_ledger(),"db_integrity":self.conn.execute("PRAGMA integrity_check").fetchone()[0]}
    def bundle(self,out):
        out=Path(out)
        with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
            for t in ["defs","flows","tasks","decisions","citizen","audit","ledger"]:
                z.writestr(f"{t}.json",json.dumps([dict(r) for r in self.conn.execute(f"SELECT * FROM {t} ORDER BY 1")],indent=2))
            z.writestr("workflow_status.json",json.dumps(self.stats(),indent=2))
        return {"bundle":str(out),"exists":out.exists()}
def seed_demo(td):
    e=WorkflowEngine(Path(td)/"workflow.db","office:north")
    renewal=e.open("credential_renewal","citizen:root",{"credential":"C-1"})
    for _ in range(5): e.auto(renewal["workflow"])
    transfer=e.open("credential_transfer","citizen:root",{"credential":"C-2"})
    for _ in range(4): e.auto(transfer["workflow"])
    susp=e.open("suspension","citizen:bad",{"reason":"revoked"})
    for _ in range(3): e.auto(susp["workflow"])
    e.decide(susp["workflow"],"operator","suspend","suspended",{})
    appeal=e.open("appeal","citizen:bad",{"appeals":"suspension"})
    for _ in range(4): e.auto(appeal["workflow"])
    case=e.open("case_review","credential:C-9",{"kind":"conflict"})
    for _ in range(4): e.auto(case["workflow"])
    invalid=e.decide(renewal["workflow"],"operator","bad","submitted",{})
    return {"renewal":renewal,"transfer":transfer,"suspension":susp,"appeal":appeal,"case":case,"invalid":invalid,"stats":e.stats(),"queue":e.queue()}
