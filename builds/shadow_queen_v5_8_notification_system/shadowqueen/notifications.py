
import json,sqlite3,time,hashlib,zipfile
from pathlib import Path
def digest(o): return hashlib.sha256(json.dumps(o,sort_keys=True,default=str).encode()).hexdigest()
class Notifications:
    def __init__(self,path="notifications.db",node="office:north",outbox="outbox"):
        self.node=node; self.outbox=Path(outbox); self.outbox.mkdir(parents=True,exist_ok=True)
        self.conn=sqlite3.connect(Path(path)); self.conn.row_factory=sqlite3.Row
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS channels(id TEXT PRIMARY KEY,kind TEXT,target TEXT,status TEXT);
        CREATE TABLE IF NOT EXISTS subs(id TEXT PRIMARY KEY,event TEXT,channel TEXT,filter TEXT,status TEXT);
        CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY,type TEXT,subject TEXT,payload TEXT,status TEXT);
        CREATE TABLE IF NOT EXISTS queue(id TEXT PRIMARY KEY,event_id TEXT,channel TEXT,status TEXT,attempts INTEGER,payload TEXT);
        CREATE TABLE IF NOT EXISTS deliveries(id INTEGER PRIMARY KEY,queue_id TEXT,channel TEXT,status TEXT,result TEXT);
        CREATE TABLE IF NOT EXISTS failures(id INTEGER PRIMARY KEY,queue_id TEXT,reason TEXT,details TEXT);
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
        for r in self.conn.execute("SELECT * FROM ledger ORDER BY seq"):
            exp=digest({"kind":r["kind"],"subject":r["subject"],"payload_hash":r["payload_hash"],"prev_hash":prev})
            if r["prev_hash"]!=prev: return {"ok":False,"seq":r["seq"],"reason":"prev_hash_mismatch"}
            if r["entry_hash"]!=exp: return {"ok":False,"seq":r["seq"],"reason":"entry_hash_mismatch"}
            prev=r["entry_hash"]; n+=1
        return {"ok":True,"entries":n,"head":prev}
    def channel(self,kind,target):
        cid="channel:"+digest({"kind":kind,"target":target})[:16]
        self.conn.execute("INSERT OR REPLACE INTO channels VALUES(?,?,?,?)",(cid,kind,target,"active"))
        self.receipt("channel",cid,{"kind":kind,"target":target}); self.conn.commit()
        return {"channel":cid,"kind":kind,"target":target}
    def subscribe(self,event,channel,filter_rule=None):
        sid="sub:"+digest({"event":event,"channel":channel,"filter":filter_rule or {}})[:16]
        self.conn.execute("INSERT OR REPLACE INTO subs VALUES(?,?,?,?,?)",(sid,event,channel,json.dumps(filter_rule or {}),"active"))
        self.receipt("subscription",sid,{"event":event,"channel":channel}); self.conn.commit()
        return {"subscription":sid}
    def match(self,flt,payload):
        return all(payload.get(k)==v for k,v in (flt or {}).items())
    def publish(self,event,subject,payload=None):
        payload=payload or {}; eid="event:"+digest({"event":event,"subject":subject,"payload":payload,"t":time.time()})[:16]
        self.conn.execute("INSERT INTO events VALUES(?,?,?,?,?)",(eid,event,subject,json.dumps(payload),"published"))
        queued=[]
        for s in self.conn.execute("SELECT * FROM subs WHERE event=? AND status='active'",(event,)):
            if not self.match(json.loads(s["filter"] or "{}"),payload): continue
            qid="notice:"+digest({"event":eid,"channel":s["channel"]})[:16]
            msg={"event_id":eid,"event":event,"subject":subject,"payload":payload,"node":self.node}
            self.conn.execute("INSERT OR REPLACE INTO queue VALUES(?,?,?,?,?,?)",(qid,eid,s["channel"],"queued",0,json.dumps(msg)))
            queued.append(qid)
        self.receipt("publish",eid,{"event":event,"queued":len(queued)}); self.conn.commit()
        return {"event":eid,"queued":queued}
    def workflow_hook(self,wid,event,subject,state,status,details=None):
        return self.publish(event,subject,{"workflow_id":wid,"state":state,"status":status,**(details or {})})
    def fail(self,qid,reason,details=None):
        self.conn.execute("UPDATE queue SET status='failed',attempts=attempts+1 WHERE id=?",(qid,))
        self.conn.execute("INSERT INTO failures(queue_id,reason,details) VALUES(?,?,?)",(qid,reason,json.dumps(details or {})))
        self.conn.execute("INSERT INTO deliveries(queue_id,channel,status,result) VALUES(?,?,?,?)",(qid,"","failed",reason))
        self.receipt("failed",qid,{"reason":reason}); self.conn.commit()
        return {"ok":False,"queue":qid,"reason":reason}
    def deliver_one(self,qid):
        q=self.conn.execute("SELECT * FROM queue WHERE id=?",(qid,)).fetchone()
        if not q: return {"ok":False,"reason":"missing"}
        ch=self.conn.execute("SELECT * FROM channels WHERE id=?",(q["channel"],)).fetchone()
        if not ch or ch["status"]!="active": return self.fail(qid,"channel_inactive")
        if ch["kind"] not in ("email","sms","operator","webhook"): return self.fail(qid,"unknown_channel",{"kind":ch["kind"]})
        msg=json.loads(q["payload"]); path=self.outbox/(ch["kind"]+"_"+digest({"qid":qid,"target":ch["target"]})[:12]+".json")
        path.write_text(json.dumps({"channel":ch["kind"],"target":ch["target"],"message":msg},indent=2))
        self.conn.execute("UPDATE queue SET status='delivered',attempts=attempts+1 WHERE id=?",(qid,))
        self.conn.execute("INSERT INTO deliveries(queue_id,channel,status,result) VALUES(?,?,?,?)",(qid,ch["id"],"delivered",str(path)))
        self.receipt("delivered",qid,{"path":str(path)}); self.conn.commit()
        return {"ok":True,"queue":qid,"status":"delivered"}
    def process(self):
        rows=list(self.conn.execute("SELECT id FROM queue WHERE status='queued' ORDER BY id"))
        out=[self.deliver_one(r["id"]) for r in rows]
        return {"processed":len(out),"delivered":len([x for x in out if x.get("ok")]),"failed":len([x for x in out if not x.get("ok")])}
    def retry_failed(self):
        self.conn.execute("UPDATE queue SET status='queued' WHERE status='failed'")
        self.receipt("retry","queue",{}); self.conn.commit()
        return self.process()
    def stats(self):
        return {"node":self.node,"channels":self.conn.execute("SELECT COUNT(*) n FROM channels").fetchone()["n"],"subscriptions":self.conn.execute("SELECT COUNT(*) n FROM subs").fetchone()["n"],"events":self.conn.execute("SELECT COUNT(*) n FROM events").fetchone()["n"],"queued":self.conn.execute("SELECT COUNT(*) n FROM queue WHERE status='queued'").fetchone()["n"],"delivered":self.conn.execute("SELECT COUNT(*) n FROM queue WHERE status='delivered'").fetchone()["n"],"failed":self.conn.execute("SELECT COUNT(*) n FROM queue WHERE status='failed'").fetchone()["n"],"delivery_logs":self.conn.execute("SELECT COUNT(*) n FROM deliveries").fetchone()["n"],"ledger":self.verify_ledger(),"db_integrity":self.conn.execute("PRAGMA integrity_check").fetchone()[0]}
    def bundle(self,out):
        out=Path(out)
        with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
            for t in ["channels","subs","events","queue","deliveries","failures","ledger"]:
                z.writestr(f"{t}.json",json.dumps([dict(r) for r in self.conn.execute(f"SELECT * FROM {t} ORDER BY 1")],indent=2))
            for p in sorted(self.outbox.glob("*.json")): z.write(p,arcname="outbox/"+p.name)
            z.writestr("notification_status.json",json.dumps(self.stats(),indent=2))
        return {"bundle":str(out),"exists":out.exists()}
def seed_demo(td):
    out=Path(td)/"outbox"; n=Notifications(Path(td)/"notifications.db","office:north",out)
    email=n.channel("email","operator@example.local"); sms=n.channel("sms","+15550101010"); op=n.channel("operator","dashboard"); bad=n.channel("badkind","broken")
    n.subscribe("workflow.closed",email["channel"])
    n.subscribe("workflow.closed",sms["channel"],{"status":"closed"})
    n.subscribe("fraud.critical",op["channel"])
    n.subscribe("fraud.critical",bad["channel"])
    e1=n.workflow_hook("workflow:renewal","workflow.closed","citizen:root","issued","closed",{"credential":"C-1"})
    e2=n.publish("fraud.critical","credential:C-9",{"severity":"critical","kind":"forged"})
    first=n.process(); retry=n.retry_failed()
    return {"workflow_event":e1,"fraud_event":e2,"first_process":first,"retry":retry,"stats":n.stats(),"outbox_files":[p.name for p in out.glob('*.json')]}
