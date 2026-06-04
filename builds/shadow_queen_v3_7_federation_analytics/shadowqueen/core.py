
import json,hashlib,sqlite3,time,zipfile
from pathlib import Path
def digest(o): return hashlib.sha256(json.dumps(o,sort_keys=True,default=str).encode()).hexdigest()
class Analytics:
    def __init__(self,path="analytics.db",domain="shadow-analytics"):
        self.domain=domain; self.conn=sqlite3.connect(Path(path)); self.conn.row_factory=sqlite3.Row
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,source TEXT,kind TEXT,subject TEXT,value REAL,severity TEXT,details TEXT);
        CREATE TABLE IF NOT EXISTS offices(office TEXT PRIMARY KEY,risk REAL,trust REAL,drift INTEGER,cases INTEGER,lag REAL,severity TEXT);
        CREATE TABLE IF NOT EXISTS dashboards(id TEXT PRIMARY KEY,status TEXT,summary TEXT,hash TEXT);
        CREATE TABLE IF NOT EXISTS recs(id INTEGER PRIMARY KEY,subject TEXT,kind TEXT,priority TEXT,details TEXT);
        CREATE TABLE IF NOT EXISTS ledger(seq INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT,subject TEXT,payload_hash TEXT,prev_hash TEXT,entry_hash TEXT);
        """); self.conn.commit()
    def last_hash(self):
        r=self.conn.execute("SELECT entry_hash FROM ledger ORDER BY seq DESC LIMIT 1").fetchone()
        return r["entry_hash"] if r else "GENESIS"
    def receipt(self,k,s,p):
        prev=self.last_hash(); ph=digest(p); eh=digest({"kind":k,"subject":s,"payload_hash":ph,"prev_hash":prev})
        self.conn.execute("INSERT INTO ledger(kind,subject,payload_hash,prev_hash,entry_hash) VALUES(?,?,?,?,?)",(k,s,ph,prev,eh)); self.conn.commit()
    def verify_ledger(self):
        prev="GENESIS"; n=0
        for r in self.conn.execute("SELECT seq,kind,subject,payload_hash,prev_hash,entry_hash FROM ledger ORDER BY seq"):
            exp=digest({"kind":r["kind"],"subject":r["subject"],"payload_hash":r["payload_hash"],"prev_hash":prev})
            if r["prev_hash"]!=prev: return {"ok":False,"seq":r["seq"],"reason":"prev_hash_mismatch"}
            if r["entry_hash"]!=exp: return {"ok":False,"seq":r["seq"],"reason":"entry_hash_mismatch"}
            prev=r["entry_hash"]; n+=1
        return {"ok":True,"entries":n,"head":prev}
    def event(self,source,kind,subject,value=1,severity="low",details=None):
        self.conn.execute("INSERT INTO events(source,kind,subject,value,severity,details) VALUES(?,?,?,?,?,?)",(source,kind,subject,float(value),severity,json.dumps(details or {})))
        self.receipt("metric",subject,{"source":source,"kind":kind,"value":value,"severity":severity}); self.conn.commit()
    def all_events(self): return [dict(r) for r in self.conn.execute("SELECT * FROM events ORDER BY id")]
    def compute(self):
        state={}
        for e in self.all_events():
            d=json.loads(e["details"] or "{}")
            office=d.get("office") or (e["subject"].split(":")[-1] if e["subject"].startswith("office:") else None)
            if not office: continue
            s=state.setdefault(office,{"risk":0,"drift":0,"cases":0,"lags":[]})
            if e["kind"]=="office_drift": s["risk"]+=20; s["drift"]+=1
            if e["kind"]=="case_opened": s["risk"]+=10; s["cases"]+=1
            if e["kind"]=="replication_lag": s["risk"]+=min(30,float(e["value"])); s["lags"].append(float(e["value"]))
            if e["severity"]=="critical": s["risk"]+=25
            elif e["severity"]=="high": s["risk"]+=15
        out=[]
        for office,s in state.items():
            risk=min(100,s["risk"]); trust=max(0,100-risk); lag=sum(s["lags"])/len(s["lags"]) if s["lags"] else 0
            sev="critical" if risk>=80 else "high" if risk>=60 else "medium" if risk>=30 else "low"
            self.conn.execute("INSERT OR REPLACE INTO offices VALUES(?,?,?,?,?,?,?)",(office,risk,trust,s["drift"],s["cases"],lag,sev))
            out.append({"office":office,"risk":risk,"trust":trust,"severity":sev})
        self.receipt("office_scores","federation",{"count":len(out)}); self.conn.commit()
        return out
    def recommendations(self):
        recs=[]
        for o in self.conn.execute("SELECT * FROM offices ORDER BY risk DESC"):
            if o["risk"]>=80: kind,pri="quarantine_office","critical"
            elif o["risk"]>=60: kind,pri="route_ops_review","high"
            elif o["risk"]>=30: kind,pri="monitor_office","medium"
            else: continue
            detail={"office":o["office"],"risk":o["risk"],"trust":o["trust"]}
            self.conn.execute("INSERT INTO recs(subject,kind,priority,details) VALUES(?,?,?,?)",("office:"+o["office"],kind,pri,json.dumps(detail)))
            recs.append({"subject":"office:"+o["office"],"kind":kind,"priority":pri})
        self.receipt("recommendations","federation",{"count":len(recs)}); self.conn.commit()
        return recs
    def dashboard(self):
        offices=self.compute(); recs=self.recommendations()
        status="critical" if any(o["severity"]=="critical" for o in offices) else "warning" if any(o["severity"] in ("high","medium") for o in offices) else "pass"
        summary={"domain":self.domain,"events":len(self.all_events()),"offices":offices,"recommendations":recs,"ledger":self.verify_ledger()}
        h=digest(summary); did="dashboard:"+h[:16]
        self.conn.execute("INSERT OR REPLACE INTO dashboards VALUES(?,?,?,?)",(did,status,json.dumps(summary),h))
        self.receipt("dashboard",did,{"status":status,"hash":h}); self.conn.commit()
        return {"dashboard":did,"status":status,"summary":summary,"hash":h}
    def stats(self):
        return {"domain":self.domain,"events":self.conn.execute("SELECT COUNT(*) n FROM events").fetchone()["n"],"offices":self.conn.execute("SELECT COUNT(*) n FROM offices").fetchone()["n"],"dashboards":self.conn.execute("SELECT COUNT(*) n FROM dashboards").fetchone()["n"],"recommendations":self.conn.execute("SELECT COUNT(*) n FROM recs").fetchone()["n"],"ledger":self.verify_ledger(),"db_integrity":self.conn.execute("PRAGMA integrity_check").fetchone()[0]}
    def bundle(self,out):
        out=Path(out)
        with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
            for t in ["events","offices","dashboards","recs","ledger"]:
                z.writestr(f"{t}.json",json.dumps([dict(r) for r in self.conn.execute(f"SELECT * FROM {t} ORDER BY 1")],indent=2,default=str))
            z.writestr("manifest.json",json.dumps({"stats":self.stats(),"created":time.time()},indent=2))
        return {"bundle":str(out),"exists":out.exists()}
def seed_demo(a):
    a.event("ops","office_drift","office:west",1,"high",{"office":"west"})
    a.event("ops","replication_lag","office:west",12,"high",{"office":"west"})
    a.event("investigation","case_opened","office:west",1,"high",{"office":"west"})
    a.event("ops","replication_lag","office:south",3,"medium",{"office":"south"})
    a.event("investigation","case_opened","office:east",1,"medium",{"office":"east"})
    a.event("fraud","fraud_signal","person:synthetic",70,"critical",{})
    return a.dashboard()
