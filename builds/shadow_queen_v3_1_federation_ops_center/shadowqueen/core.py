
import json,hashlib,sqlite3,time,zipfile
from pathlib import Path
def digest(o): return hashlib.sha256(json.dumps(o,sort_keys=True,default=str).encode()).hexdigest()
class FederationOps:
    def __init__(self,path="ops.db",fid="shadow-federation"):
        self.fid=fid; self.conn=sqlite3.connect(Path(path)); self.conn.row_factory=sqlite3.Row
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS offices(id TEXT PRIMARY KEY,region TEXT,endpoint TEXT,status TEXT,trust REAL,last_seen REAL,meta TEXT);
        CREATE TABLE IF NOT EXISTS health(id INTEGER PRIMARY KEY,ts REAL,office TEXT,status TEXT,latency REAL,lag INTEGER,errors INTEGER,details TEXT);
        CREATE TABLE IF NOT EXISTS drift(id INTEGER PRIMARY KEY,ts REAL,office TEXT,kind TEXT,severity TEXT,status TEXT,details TEXT);
        CREATE TABLE IF NOT EXISTS cases(id TEXT PRIMARY KEY,ts REAL,subject TEXT,kind TEXT,severity TEXT,assigned TEXT,status TEXT,details TEXT);
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,ts REAL,type TEXT,subject TEXT,details TEXT);
        CREATE TABLE IF NOT EXISTS recovery(id INTEGER PRIMARY KEY,ts REAL,office TEXT,action TEXT,actor TEXT,result TEXT,details TEXT);
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
    def event(self,t,sub,d=None):
        self.conn.execute("INSERT INTO events(ts,type,subject,details) VALUES(?,?,?,?)",(time.time(),t,sub,json.dumps(d or {},default=str)))
        self.receipt("event",sub,{"type":t,"details":d or {}})
    def register(self,office,region="unknown",endpoint="",trust=75,meta=None):
        self.conn.execute("INSERT OR REPLACE INTO offices VALUES(?,?,?,?,?,?,?)",(office,region,endpoint,"active",float(trust),time.time(),json.dumps(meta or {})))
        self.event("office_registered",office,{"region":region,"trust":trust}); self.conn.commit()
        return {"office":office,"status":"active","trust":trust}
    def heartbeat(self,office,status="healthy",latency=0,lag=0,errors=0,details=None):
        state="degraded" if status!="healthy" or lag>5 or errors>0 else "active"
        self.conn.execute("INSERT INTO health(ts,office,status,latency,lag,errors,details) VALUES(?,?,?,?,?,?,?)",(time.time(),office,status,float(latency),int(lag),int(errors),json.dumps(details or {})))
        self.conn.execute("UPDATE offices SET status=?,last_seen=? WHERE id=?",(state,time.time(),office))
        self.event("heartbeat",office,{"status":status,"lag":lag,"errors":errors}); self.conn.commit()
        return {"office":office,"status":state}
    def adjust_trust(self,office,delta,reason):
        r=self.conn.execute("SELECT trust FROM offices WHERE id=?",(office,)).fetchone()
        if not r: return {"ok":False,"reason":"missing_office"}
        trust=max(0,min(100,float(r["trust"])+float(delta)))
        status="quarantined" if trust<30 else "degraded" if trust<60 else "active"
        self.conn.execute("UPDATE offices SET trust=?,status=? WHERE id=?",(trust,status,office))
        self.event("trust_adjusted",office,{"delta":delta,"reason":reason,"trust":trust,"status":status}); self.conn.commit()
        return {"ok":True,"office":office,"trust":trust,"status":status}
    def record_drift(self,office,kind,severity="medium",details=None):
        self.conn.execute("INSERT INTO drift(ts,office,kind,severity,status,details) VALUES(?,?,?,?,?,?)",(time.time(),office,kind,severity,"open",json.dumps(details or {},default=str)))
        penalty={"low":2,"medium":7,"high":15,"critical":30}.get(severity,7)
        self.adjust_trust(office,-penalty,f"drift:{kind}")
        self.event("drift",office,{"kind":kind,"severity":severity}); self.conn.commit()
        return {"office":office,"kind":kind,"severity":severity,"penalty":penalty}
    def quarantine(self,office,actor="ops",reason="manual"):
        self.conn.execute("UPDATE offices SET status='quarantined' WHERE id=?",(office,))
        self.conn.execute("INSERT INTO recovery(ts,office,action,actor,result,details) VALUES(?,?,?,?,?,?)",(time.time(),office,"quarantine",actor,"ok",json.dumps({"reason":reason})))
        self.event("quarantine",office,{"actor":actor,"reason":reason}); self.conn.commit()
        return {"office":office,"status":"quarantined"}
    def recover(self,office,actor="ops",reason="manual"):
        self.conn.execute("UPDATE offices SET status='active',trust=MAX(trust,60) WHERE id=?",(office,))
        self.conn.execute("UPDATE drift SET status='resolved' WHERE office=? AND status='open'",(office,))
        self.conn.execute("INSERT INTO recovery(ts,office,action,actor,result,details) VALUES(?,?,?,?,?,?)",(time.time(),office,"recover",actor,"ok",json.dumps({"reason":reason})))
        self.event("recover",office,{"actor":actor,"reason":reason}); self.conn.commit()
        return {"office":office,"status":"active"}
    def route_case(self,subject,kind,severity="medium",details=None):
        offices=[dict(r) for r in self.conn.execute("SELECT * FROM offices WHERE status='active' ORDER BY trust DESC,last_seen DESC")]
        assigned=offices[0]["id"] if offices else "unassigned"
        cid="case:"+digest({"subject":subject,"kind":kind,"ts":time.time()})[:16]
        self.conn.execute("INSERT INTO cases VALUES(?,?,?,?,?,?,?,?)",(cid,time.time(),subject,kind,severity,assigned,"open",json.dumps(details or {},default=str)))
        self.event("case_routed",cid,{"assigned":assigned,"subject":subject,"kind":kind}); self.conn.commit()
        return {"case":cid,"assigned":assigned,"status":"open"}
    def validate_credential(self,cred,reports):
        groups={}
        for off,st in reports.items(): groups.setdefault(st,[]).append(off)
        if len(groups)==1:
            res={"credential":cred,"valid":True,"status":list(groups)[0],"reports":reports}; self.event("credential_validated",cred,res); return res
        self.record_drift("federation","credential_status_disagreement","high",{"credential":cred,"reports":reports})
        return {"credential":cred,"valid":False,"case":self.route_case(cred,"credential_status_disagreement","high",{"reports":reports})}
    def offices(self): return [dict(r) for r in self.conn.execute("SELECT * FROM offices ORDER BY id")]
    def cases(self): return [dict(r) for r in self.conn.execute("SELECT * FROM cases ORDER BY ts")]
    def drift(self): return [dict(r) for r in self.conn.execute("SELECT * FROM drift ORDER BY id")]
    def dashboard(self):
        offices=self.offices(); open_d=[d for d in self.drift() if d["status"]=="open"]; open_c=[c for c in self.cases() if c["status"]=="open"]
        return {"federation":self.fid,"office_count":len(offices),"average_trust":round(sum(float(o["trust"]) for o in offices)/max(1,len(offices)),2),"quarantined":[o["id"] for o in offices if o["status"]=="quarantined"],"degraded":[o["id"] for o in offices if o["status"]=="degraded"],"open_drift":len(open_d),"open_cases":len(open_c),"ledger":self.verify_ledger()}
    def stats(self):
        return {"federation":self.fid,"offices":self.conn.execute("SELECT COUNT(*) n FROM offices").fetchone()["n"],"health":self.conn.execute("SELECT COUNT(*) n FROM health").fetchone()["n"],"drift":self.conn.execute("SELECT COUNT(*) n FROM drift").fetchone()["n"],"cases":self.conn.execute("SELECT COUNT(*) n FROM cases").fetchone()["n"],"events":self.conn.execute("SELECT COUNT(*) n FROM events").fetchone()["n"],"recovery":self.conn.execute("SELECT COUNT(*) n FROM recovery").fetchone()["n"],"ledger":self.verify_ledger(),"db_integrity":self.conn.execute("PRAGMA integrity_check").fetchone()[0]}
    def bundle(self,out):
        out=Path(out)
        with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
            for t in ["offices","health","drift","cases","events","recovery","ledger"]:
                z.writestr(f"{t}.json",json.dumps([dict(r) for r in self.conn.execute(f"SELECT * FROM {t} ORDER BY 1")],indent=2,default=str))
            z.writestr("dashboard.json",json.dumps(self.dashboard(),indent=2,default=str))
            z.writestr("manifest.json",json.dumps({"stats":self.stats(),"created":time.time()},indent=2))
        return {"bundle":str(out),"exists":out.exists()}
def seed_demo(ops):
    for office,region,trust in [("north","MN",88),("south","IA",73),("east","WI",81),("west","ND",55)]:
        ops.register(office,region,f"local://{office}",trust)
    ops.heartbeat("north","healthy",20,0,0); ops.heartbeat("south","healthy",35,2,0); ops.heartbeat("east","healthy",25,0,0); ops.heartbeat("west","timeout",900,12,3)
    ops.record_drift("west","replication_lag","high",{"lag":12})
    ops.validate_credential("credential:C-1",{"north":"active","south":"active","east":"revoked"})
    return ops.dashboard()
