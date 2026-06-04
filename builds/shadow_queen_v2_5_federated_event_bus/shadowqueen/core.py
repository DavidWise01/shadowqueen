
import json, hashlib, sqlite3, time, zipfile
from pathlib import Path
from dataclasses import dataclass, field

def digest(o):
    return hashlib.sha256(json.dumps(o,sort_keys=True,default=str).encode()).hexdigest()

@dataclass(frozen=True)
class FederatedEvent:
    event_id:str
    origin_office:str
    event_type:str
    subject:str
    payload:dict=field(default_factory=dict)
    causal_chain:list=field(default_factory=list)
    ts:float=0.0
    event_hash:str=""

    @classmethod
    def create(cls,origin,event_type,subject,payload=None,causal_chain=None):
        ts=time.time()
        base={"origin_office":origin,"event_type":event_type,"subject":subject,"payload":payload or {},"causal_chain":causal_chain or [],"ts":ts}
        eid=digest(base)
        eh=digest({**base,"event_id":eid})
        return cls(eid,origin,event_type,subject,payload or {},causal_chain or [],ts,eh)

    def verify(self):
        base={"origin_office":self.origin_office,"event_type":self.event_type,"subject":self.subject,"payload":self.payload,"causal_chain":self.causal_chain,"ts":self.ts}
        return self.event_id==digest(base) and self.event_hash==digest({**base,"event_id":self.event_id})

    def to_dict(self):
        return self.__dict__

class Store:
    def __init__(self,path="event_bus.db",office_id="north"):
        self.office_id=office_id
        self.conn=sqlite3.connect(Path(path))
        self.conn.row_factory=sqlite3.Row
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS events(event_id TEXT PRIMARY KEY,origin_office TEXT,event_type TEXT,subject TEXT,event_hash TEXT,ts REAL,payload_json TEXT,causal_chain_json TEXT,verified INTEGER,applied INTEGER);
        CREATE TABLE IF NOT EXISTS outbox(id INTEGER PRIMARY KEY,ts REAL,event_id TEXT,target_office TEXT,status TEXT,attempts INTEGER,last_error TEXT);
        CREATE TABLE IF NOT EXISTS inbox(id INTEGER PRIMARY KEY,ts REAL,event_id TEXT,from_office TEXT,status TEXT,reason TEXT);
        CREATE TABLE IF NOT EXISTS receipts(id INTEGER PRIMARY KEY,ts REAL,event_id TEXT,office_id TEXT,receipt_hash TEXT,status TEXT,details_json TEXT);
        CREATE TABLE IF NOT EXISTS delivery(id INTEGER PRIMARY KEY,ts REAL,event_id TEXT,target_office TEXT,status TEXT,details_json TEXT);
        CREATE TABLE IF NOT EXISTS audits(id INTEGER PRIMARY KEY,ts REAL,auditor TEXT,result TEXT,details_json TEXT);
        CREATE TABLE IF NOT EXISTS ledger(seq INTEGER PRIMARY KEY AUTOINCREMENT,ts REAL,kind TEXT,subject TEXT,payload_hash TEXT,prev_hash TEXT,entry_hash TEXT);
        """)
        self.conn.commit()

    def last_hash(self):
        r=self.conn.execute("SELECT entry_hash FROM ledger ORDER BY seq DESC LIMIT 1").fetchone()
        return r["entry_hash"] if r else "GENESIS"

    def receipt(self,kind,subject,payload):
        prev=self.last_hash()
        ph=digest(payload)
        eh=digest({"kind":kind,"subject":subject,"payload_hash":ph,"prev_hash":prev})
        self.conn.execute("INSERT INTO ledger(ts,kind,subject,payload_hash,prev_hash,entry_hash) VALUES(?,?,?,?,?,?)",(time.time(),kind,subject,ph,prev,eh))
        return eh

    def verify_ledger(self):
        prev="GENESIS"; n=0
        for r in self.conn.execute("SELECT seq,kind,subject,payload_hash,prev_hash,entry_hash FROM ledger ORDER BY seq"):
            exp=digest({"kind":r["kind"],"subject":r["subject"],"payload_hash":r["payload_hash"],"prev_hash":prev})
            if r["prev_hash"]!=prev:
                return {"ok":False,"seq":r["seq"],"reason":"prev_hash_mismatch"}
            if r["entry_hash"]!=exp:
                return {"ok":False,"seq":r["seq"],"reason":"entry_hash_mismatch"}
            prev=r["entry_hash"]; n+=1
        return {"ok":True,"entries":n,"head":prev}

    def has_event(self,eid):
        return self.conn.execute("SELECT 1 FROM events WHERE event_id=?",(eid,)).fetchone() is not None

    def store_event(self,event,applied=False):
        ok=event.verify()
        self.conn.execute("INSERT OR IGNORE INTO events VALUES(?,?,?,?,?,?,?,?,?,?)",(event.event_id,event.origin_office,event.event_type,event.subject,event.event_hash,event.ts,json.dumps(event.payload),json.dumps(event.causal_chain),1 if ok else 0,1 if applied else 0))
        status="accepted" if ok else "rejected"
        rh=self.receipt("event_store",event.event_id,{"verified":ok,"office":self.office_id})
        self.conn.execute("INSERT INTO receipts(ts,event_id,office_id,receipt_hash,status,details_json) VALUES(?,?,?,?,?,?)",(time.time(),event.event_id,self.office_id,rh,status,json.dumps({"event_type":event.event_type,"subject":event.subject})))
        self.conn.commit()
        return {"event_id":event.event_id,"verified":ok,"status":status}

    def publish(self,event_type,subject,payload=None,targets=None,causal_chain=None):
        ev=FederatedEvent.create(self.office_id,event_type,subject,payload or {},causal_chain or [])
        self.store_event(ev,True)
        for target in targets or []:
            self.conn.execute("INSERT INTO outbox(ts,event_id,target_office,status,attempts,last_error) VALUES(?,?,?,?,?,?)",(time.time(),ev.event_id,target,"queued",0,""))
            self.conn.execute("INSERT INTO delivery(ts,event_id,target_office,status,details_json) VALUES(?,?,?,?,?)",(time.time(),ev.event_id,target,"queued","{}"))
        self.receipt("event_publish",ev.event_id,{"targets":targets or [],"type":event_type})
        self.conn.commit()
        return ev

    def get_event(self,eid):
        r=self.conn.execute("SELECT * FROM events WHERE event_id=?",(eid,)).fetchone()
        if not r:
            return None
        return FederatedEvent(r["event_id"],r["origin_office"],r["event_type"],r["subject"],json.loads(r["payload_json"]),json.loads(r["causal_chain_json"]),r["ts"],r["event_hash"])

    def receive(self,event,from_office):
        if self.has_event(event.event_id):
            self.conn.execute("INSERT INTO inbox(ts,event_id,from_office,status,reason) VALUES(?,?,?,?,?)",(time.time(),event.event_id,from_office,"duplicate","already_seen"))
            self.receipt("event_duplicate",event.event_id,{"from":from_office})
            self.conn.commit()
            return {"accepted":False,"status":"duplicate","reason":"already_seen"}
        res=self.store_event(event,True)
        status="accepted" if res["verified"] else "rejected"
        reason="" if res["verified"] else "hash_verification_failed"
        self.conn.execute("INSERT INTO inbox(ts,event_id,from_office,status,reason) VALUES(?,?,?,?,?)",(time.time(),event.event_id,from_office,status,reason))
        self.receipt("event_receive",event.event_id,{"from":from_office,"status":status})
        self.conn.commit()
        return {"accepted":res["verified"],"status":status,"reason":reason}

    def mark_delivered(self,event_id,target,status,details=None):
        self.conn.execute("UPDATE outbox SET status=?,attempts=attempts+1,last_error=? WHERE event_id=? AND target_office=?",(status,(details or {}).get("error",""),event_id,target))
        self.conn.execute("INSERT INTO delivery(ts,event_id,target_office,status,details_json) VALUES(?,?,?,?,?)",(time.time(),event_id,target,status,json.dumps(details or {})))
        self.receipt("delivery_status",event_id,{"target":target,"status":status,"details":details or {}})
        self.conn.commit()

    def pending(self):
        return [dict(r) for r in self.conn.execute("SELECT * FROM outbox WHERE status='queued' ORDER BY id")]

    def event_ids(self):
        return sorted([r["event_id"] for r in self.conn.execute("SELECT event_id FROM events")])

    def audit_convergence(self,peers,auditor="auditor"):
        local=set(self.event_ids())
        report={"office":self.office_id,"missing_local":{},"missing_remote":{}}
        result="pass"
        for peer in peers:
            remote=set(peer.event_ids())
            ml=sorted(list(remote-local))
            mr=sorted(list(local-remote))
            report["missing_local"][peer.office_id]=ml
            report["missing_remote"][peer.office_id]=mr
            if ml or mr:
                result="warning"
        self.conn.execute("INSERT INTO audits(ts,auditor,result,details_json) VALUES(?,?,?,?)",(time.time(),auditor,result,json.dumps(report)))
        self.receipt("convergence_audit",auditor,{"result":result,"report":report})
        self.conn.commit()
        return {"result":result,"report":report}

    def stats(self):
        return {"office_id":self.office_id,"events":self.conn.execute("SELECT COUNT(*) n FROM events").fetchone()["n"],"outbox":self.conn.execute("SELECT COUNT(*) n FROM outbox").fetchone()["n"],"inbox":self.conn.execute("SELECT COUNT(*) n FROM inbox").fetchone()["n"],"receipts":self.conn.execute("SELECT COUNT(*) n FROM receipts").fetchone()["n"],"delivery":self.conn.execute("SELECT COUNT(*) n FROM delivery").fetchone()["n"],"audits":self.conn.execute("SELECT COUNT(*) n FROM audits").fetchone()["n"],"ledger":self.verify_ledger(),"db_integrity":self.conn.execute("PRAGMA integrity_check").fetchone()[0]}

    def events(self):
        return [dict(r) for r in self.conn.execute("SELECT event_id,origin_office,event_type,subject,verified,applied FROM events ORDER BY ts")]

    def bundle(self,out):
        out=Path(out)
        with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
            for t in ["events","outbox","inbox","receipts","delivery","audits","ledger"]:
                rows=[dict(r) for r in self.conn.execute(f"SELECT * FROM {t} ORDER BY 1")]
                z.writestr(f"{t}.json",json.dumps(rows,indent=2,default=str))
            z.writestr("manifest.json",json.dumps({"stats":self.stats(),"created":time.time()},indent=2))
        return {"bundle":str(out),"exists":out.exists()}

class EventBus:
    def __init__(self,store):
        self.store=store
    def publish(self,event_type,subject,payload=None,targets=None,causal_chain=None):
        return self.store.publish(event_type,subject,payload,targets,causal_chain)
    def deliver_to(self,target_store,event_id):
        ev=self.store.get_event(event_id)
        if not ev:
            return {"delivered":False,"reason":"missing_event"}
        res=target_store.receive(ev,self.store.office_id)
        self.store.mark_delivered(event_id,target_store.office_id,"delivered" if res["accepted"] else res["status"],res)
        return {"delivered":res["accepted"],"result":res}
    def replay(self,peer_map):
        out=[]
        for row in self.store.pending():
            peer=peer_map.get(row["target_office"])
            if not peer:
                self.store.mark_delivered(row["event_id"],row["target_office"],"no_peer",{"error":"target peer unavailable"})
                continue
            out.append(self.deliver_to(peer,row["event_id"]))
        return out
