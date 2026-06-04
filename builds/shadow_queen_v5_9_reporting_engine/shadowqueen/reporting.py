
import json, sqlite3, time, hashlib, zipfile
from pathlib import Path

def digest(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()

class Reporting:
    def __init__(self, path="reports.db", node="office:north", report_dir="reports"):
        self.node=node
        self.report_dir=Path(report_dir); self.report_dir.mkdir(parents=True, exist_ok=True)
        self.conn=sqlite3.connect(Path(path)); self.conn.row_factory=sqlite3.Row
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS reports(id TEXT PRIMARY KEY,kind TEXT,subject TEXT,status TEXT,h TEXT,path TEXT,payload TEXT);
        CREATE TABLE IF NOT EXISTS evidence(id TEXT PRIMARY KEY,report_id TEXT,kind TEXT,subject TEXT,h TEXT,payload TEXT);
        CREATE TABLE IF NOT EXISTS packets(id TEXT PRIMARY KEY,subject TEXT,status TEXT,h TEXT,path TEXT,manifest TEXT);
        CREATE TABLE IF NOT EXISTS receipts(id INTEGER PRIMARY KEY,kind TEXT,subject TEXT,payload_hash TEXT,receipt_hash TEXT);
        CREATE TABLE IF NOT EXISTS ledger(seq INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT,subject TEXT,payload_hash TEXT,prev_hash TEXT,entry_hash TEXT);
        """)
        self.conn.commit()

    def last_hash(self):
        r=self.conn.execute("SELECT entry_hash FROM ledger ORDER BY seq DESC LIMIT 1").fetchone()
        return r["entry_hash"] if r else "GENESIS"

    def receipt(self, kind, subject, payload):
        ph=digest(payload); rh=digest({"kind":kind,"subject":subject,"payload_hash":ph,"t":time.time()})
        prev=self.last_hash(); eh=digest({"kind":kind,"subject":subject,"payload_hash":ph,"prev_hash":prev})
        self.conn.execute("INSERT INTO receipts(kind,subject,payload_hash,receipt_hash) VALUES(?,?,?,?)",(kind,subject,ph,rh))
        self.conn.execute("INSERT INTO ledger(kind,subject,payload_hash,prev_hash,entry_hash) VALUES(?,?,?,?,?)",(kind,subject,ph,prev,eh))
        self.conn.commit()
        return {"payload_hash":ph,"receipt_hash":rh,"entry_hash":eh}

    def verify_ledger(self):
        prev="GENESIS"; n=0
        for r in self.conn.execute("SELECT * FROM ledger ORDER BY seq"):
            exp=digest({"kind":r["kind"],"subject":r["subject"],"payload_hash":r["payload_hash"],"prev_hash":prev})
            if r["prev_hash"]!=prev: return {"ok":False,"seq":r["seq"],"reason":"prev_hash_mismatch"}
            if r["entry_hash"]!=exp: return {"ok":False,"seq":r["seq"],"reason":"entry_hash_mismatch"}
            prev=r["entry_hash"]; n+=1
        return {"ok":True,"entries":n,"head":prev}

    def write_report(self, kind, subject, title, sections):
        payload={"version":"5.9.0","node":self.node,"kind":kind,"subject":subject,"title":title,"sections":sections,"created":time.time()}
        h=digest(payload); rid="report:"+h[:16]
        path=self.report_dir/(rid.replace(":","_")+".json")
        path.write_text(json.dumps(payload,indent=2,default=str))
        self.conn.execute("INSERT OR REPLACE INTO reports VALUES(?,?,?,?,?,?,?)",(rid,kind,subject,"created",h,str(path),json.dumps(payload,default=str)))
        self.conn.commit()
        self.receipt("report",rid,{"kind":kind,"subject":subject,"hash":h})
        return {"report":rid,"kind":kind,"subject":subject,"hash":h,"path":str(path)}

    def add_evidence(self, rid, kind, subject, payload):
        wrapped={"kind":kind,"subject":subject,"payload":payload,"report_id":rid}
        h=digest(wrapped); eid="evidence:"+h[:16]
        self.conn.execute("INSERT OR REPLACE INTO evidence VALUES(?,?,?,?,?,?)",(eid,rid,kind,subject,h,json.dumps(wrapped,default=str)))
        self.conn.commit()
        self.receipt("evidence",eid,{"report":rid,"kind":kind,"hash":h})
        return {"evidence":eid,"hash":h}

    def audit_report(self):
        r=self.write_report("audit","federation","Federation Audit Report",[
            {"heading":"Ledger Integrity","status":"pass","details":self.verify_ledger()},
            {"heading":"Controls","status":"pass","details":{"audit_logging":True,"hash_receipts":True,"evidence_packets":True}}
        ])
        self.add_evidence(r["report"],"audit_control","federation",{"audit_logging":True})
        return r

    def workflow_report(self, wid):
        r=self.write_report("workflow",wid,"Workflow Report",[
            {"heading":"Workflow State","details":{"workflow":wid,"state":"issued","status":"closed"}},
            {"heading":"Decision Trail","details":["submitted","reviewed","approved","issued"]}
        ])
        self.add_evidence(r["report"],"workflow_state",wid,{"state":"issued","status":"closed"})
        return r

    def credential_report(self, cid):
        r=self.write_report("credential",cid,"Credential Report",[
            {"heading":"Status","details":{"credential":cid,"status":"active"}},
            {"heading":"Verification","details":{"signature_verified":True,"revocation_checked":True}}
        ])
        self.add_evidence(r["report"],"credential_status",cid,{"status":"active"})
        return r

    def fraud_report(self, case_id):
        r=self.write_report("fraud",case_id,"Fraud Report",[
            {"heading":"Signal","details":{"case":case_id,"kind":"forged_credential","severity":"high"}},
            {"heading":"Containment","details":{"investigation_opened":True,"notification_sent":True}}
        ])
        self.add_evidence(r["report"],"fraud_signal",case_id,{"kind":"forged_credential","severity":"high"})
        return r

    def authority_report(self, gid):
        r=self.write_report("authority",gid,"Authority Report",[
            {"heading":"Grant","details":{"grant":gid,"status":"active"}},
            {"heading":"Scope","details":{"scope_verified":True,"overreach_denied":True}}
        ])
        self.add_evidence(r["report"],"authority_grant",gid,{"status":"active"})
        return r

    def federation_report(self):
        r=self.write_report("federation","cluster","Federation Health Report",[
            {"heading":"Offices","details":{"north":"healthy","south":"healthy","east":"healthy","west":"degraded"}},
            {"heading":"Mesh","details":{"replication":"ok","persistence":"ok","crypto":"ok"}}
        ])
        self.add_evidence(r["report"],"federation_health","cluster",{"offices":4,"healthy":3,"degraded":1})
        return r

    def reports(self):
        return [dict(r) for r in self.conn.execute("SELECT id,kind,subject,status,h,path FROM reports ORDER BY id")]

    def make_packet(self, subject="release"):
        reps=[dict(r) for r in self.conn.execute("SELECT * FROM reports ORDER BY id")]
        evs=[dict(r) for r in self.conn.execute("SELECT * FROM evidence ORDER BY id")]
        manifest={"subject":subject,"node":self.node,"reports":[{"id":r["id"],"kind":r["kind"],"hash":r["h"]} for r in reps],"evidence":[{"id":e["id"],"kind":e["kind"],"hash":e["h"]} for e in evs],"created":time.time()}
        h=digest(manifest); pid="packet:"+h[:16]
        out=Path("packets")/(pid.replace(":","_")+".zip"); out.parent.mkdir(exist_ok=True)
        with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
            z.writestr("manifest.json",json.dumps(manifest,indent=2,default=str))
            z.writestr("reports_index.json",json.dumps(self.reports(),indent=2,default=str))
            z.writestr("evidence_index.json",json.dumps(evs,indent=2,default=str))
            for r in reps:
                p=Path(r["path"])
                if p.exists(): z.write(p,arcname="reports/"+p.name)
        self.conn.execute("INSERT OR REPLACE INTO packets VALUES(?,?,?,?,?,?)",(pid,subject,"created",h,str(out),json.dumps(manifest,default=str)))
        self.conn.commit()
        self.receipt("packet",pid,{"subject":subject,"hash":h,"reports":len(reps),"evidence":len(evs)})
        return {"packet":pid,"hash":h,"path":str(out),"reports":len(reps),"evidence":len(evs)}

    def stats(self):
        return {"node":self.node,"reports":self.conn.execute("SELECT COUNT(*) n FROM reports").fetchone()["n"],"evidence":self.conn.execute("SELECT COUNT(*) n FROM evidence").fetchone()["n"],"packets":self.conn.execute("SELECT COUNT(*) n FROM packets").fetchone()["n"],"receipts":self.conn.execute("SELECT COUNT(*) n FROM receipts").fetchone()["n"],"ledger":self.verify_ledger(),"db_integrity":self.conn.execute("PRAGMA integrity_check").fetchone()[0]}

    def bundle(self,out):
        out=Path(out)
        with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
            for t in ["reports","evidence","packets","receipts","ledger"]:
                z.writestr(f"{t}.json",json.dumps([dict(r) for r in self.conn.execute(f"SELECT * FROM {t} ORDER BY 1")],indent=2,default=str))
            z.writestr("reporting_status.json",json.dumps(self.stats(),indent=2))
            for p in sorted(self.report_dir.glob("*.json")):
                z.write(p,arcname="reports/"+p.name)
        return {"bundle":str(out),"exists":out.exists()}

def seed_demo(td):
    e=Reporting(Path(td)/"reports.db","office:north",Path(td)/"reports")
    audit=e.audit_report()
    workflow=e.workflow_report("workflow:renewal")
    credential=e.credential_report("credential:C-1")
    fraud=e.fraud_report("case:F-1")
    authority=e.authority_report("grant:G-1")
    federation=e.federation_report()
    packet=e.make_packet("v5.9-release")
    return {"audit":audit,"workflow":workflow,"credential":credential,"fraud":fraud,"authority":authority,"federation":federation,"packet":packet,"stats":e.stats()}
