
import json, hashlib, sqlite3, time, zipfile
from pathlib import Path
from dataclasses import dataclass, field

def digest(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,default=str).encode()).hexdigest()

@dataclass(frozen=True)
class PeerNode:
    node_id:str
    node_type:str="office"
    trust_score:float=0.5
    status:str="active"
    def fingerprint(self): return digest(self.__dict__)

@dataclass(frozen=True)
class P2PMessage:
    msg_id:str
    from_node:str
    to_node:str
    kind:str
    payload:dict=field(default_factory=dict)
    ts:float=0.0
    nonce:str=""
    ttl_seconds:int=300
    signature:str=""
    @classmethod
    def create(cls,src,dst,kind,payload,ttl=300):
        ts=time.time()
        nonce=digest({"src":src,"dst":dst,"kind":kind,"payload":payload,"ts":ts})[:24]
        msg_id=digest({"src":src,"dst":dst,"kind":kind,"payload":payload,"ts":ts,"nonce":nonce,"ttl":ttl})
        sig=digest({"msg_id":msg_id,"from_node":src,"payload":payload,"nonce":nonce})
        return cls(msg_id,src,dst,kind,payload,ts,nonce,ttl,sig)
    @classmethod
    def from_row(cls,row):
        return cls(row["msg_id"],row["from_node"],row["to_node"],row["kind"],json.loads(row["payload_json"]),row["ts"],row["nonce"],row["ttl_seconds"],row["signature"])
    def verify_signature(self):
        return self.signature==digest({"msg_id":self.msg_id,"from_node":self.from_node,"payload":self.payload,"nonce":self.nonce})
    def expired(self):
        return time.time()>self.ts+self.ttl_seconds

class Store:
    def __init__(self,path="p2p.db",node_id="queen"):
        self.node_id=node_id
        self.conn=sqlite3.connect(Path(path)); self.conn.row_factory=sqlite3.Row
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS nodes(node_id TEXT PRIMARY KEY,node_type TEXT,trust_score REAL,status TEXT,fingerprint TEXT,updated_ts REAL);
        CREATE TABLE IF NOT EXISTS inbox(msg_id TEXT PRIMARY KEY,ts REAL,from_node TEXT,to_node TEXT,kind TEXT,nonce TEXT,ttl_seconds INTEGER,signature TEXT,verified INTEGER,status TEXT,payload_json TEXT);
        CREATE TABLE IF NOT EXISTS outbox(msg_id TEXT PRIMARY KEY,ts REAL,from_node TEXT,to_node TEXT,kind TEXT,nonce TEXT,ttl_seconds INTEGER,signature TEXT,status TEXT,payload_json TEXT);
        CREATE TABLE IF NOT EXISTS seen_nonces(nonce TEXT,from_node TEXT,first_seen REAL,msg_id TEXT,PRIMARY KEY(nonce,from_node));
        CREATE TABLE IF NOT EXISTS rate_limits(node_id TEXT PRIMARY KEY,window_start REAL,count INTEGER);
        CREATE TABLE IF NOT EXISTS conflicts(id INTEGER PRIMARY KEY,ts REAL,source_node TEXT,subject TEXT,kind TEXT,severity TEXT,status TEXT,details_json TEXT);
        CREATE TABLE IF NOT EXISTS ledger(seq INTEGER PRIMARY KEY AUTOINCREMENT,ts REAL,kind TEXT,subject TEXT,payload_hash TEXT,prev_hash TEXT,entry_hash TEXT);
        """); self.conn.commit()
    def last_hash(self):
        r=self.conn.execute("SELECT entry_hash FROM ledger ORDER BY seq DESC LIMIT 1").fetchone()
        return r["entry_hash"] if r else "GENESIS"
    def receipt(self,kind,subject,payload):
        prev=self.last_hash(); ph=digest(payload); eh=digest({"kind":kind,"subject":subject,"payload_hash":ph,"prev_hash":prev})
        self.conn.execute("INSERT INTO ledger(ts,kind,subject,payload_hash,prev_hash,entry_hash) VALUES(?,?,?,?,?,?)",(time.time(),kind,subject,ph,prev,eh)); self.conn.commit()
    def verify_ledger(self):
        prev="GENESIS"; n=0
        for r in self.conn.execute("SELECT seq,kind,subject,payload_hash,prev_hash,entry_hash FROM ledger ORDER BY seq"):
            exp=digest({"kind":r["kind"],"subject":r["subject"],"payload_hash":r["payload_hash"],"prev_hash":prev})
            if r["prev_hash"]!=prev: return {"ok":False,"seq":r["seq"],"reason":"prev_hash_mismatch"}
            if r["entry_hash"]!=exp: return {"ok":False,"seq":r["seq"],"reason":"entry_hash_mismatch"}
            prev=r["entry_hash"]; n+=1
        return {"ok":True,"entries":n,"head":prev}
    def register_node(self,node):
        fp=node.fingerprint()
        self.conn.execute("INSERT OR REPLACE INTO nodes VALUES(?,?,?,?,?,?)",(node.node_id,node.node_type,node.trust_score,node.status,fp,time.time()))
        self.receipt("node_registered",node.node_id,{"fp":fp,"trust":node.trust_score})
    def peer(self,node_id):
        r=self.conn.execute("SELECT status,trust_score FROM nodes WHERE node_id=?",(node_id,)).fetchone()
        return dict(r) if r else {"status":"unknown","trust_score":0.0}
    def penalize(self,node_id,points,reason):
        r=self.conn.execute("SELECT trust_score FROM nodes WHERE node_id=?",(node_id,)).fetchone()
        if r:
            score=max(0,float(r["trust_score"])-points)
            status="quarantined" if score<0.2 else "active"
            self.conn.execute("UPDATE nodes SET trust_score=?,status=?,updated_ts=? WHERE node_id=?",(score,status,time.time(),node_id))
        self.receipt("peer_penalty",node_id,{"points":points,"reason":reason})
    def rate_ok(self,node_id,limit=10,window=60):
        now=time.time()
        r=self.conn.execute("SELECT window_start,count FROM rate_limits WHERE node_id=?",(node_id,)).fetchone()
        if not r or now-r["window_start"]>window:
            self.conn.execute("INSERT OR REPLACE INTO rate_limits VALUES(?,?,?)",(node_id,now,1)); self.conn.commit(); return True
        count=r["count"]+1
        self.conn.execute("UPDATE rate_limits SET count=? WHERE node_id=?",(count,node_id)); self.conn.commit()
        return count<=limit
    def nonce_seen(self,msg):
        return self.conn.execute("SELECT 1 FROM seen_nonces WHERE nonce=? AND from_node=?",(msg.nonce,msg.from_node)).fetchone() is not None
    def remember_nonce(self,msg):
        self.conn.execute("INSERT OR REPLACE INTO seen_nonces VALUES(?,?,?,?)",(msg.nonce,msg.from_node,time.time(),msg.msg_id)); self.conn.commit()
    def queue_outbox(self,msg):
        self.conn.execute("INSERT OR REPLACE INTO outbox VALUES(?,?,?,?,?,?,?,?,?,?)",(msg.msg_id,msg.ts,msg.from_node,msg.to_node,msg.kind,msg.nonce,msg.ttl_seconds,msg.signature,"queued",json.dumps(msg.payload)))
        self.receipt("outbox_queued",msg.msg_id,msg.__dict__)
    def receive(self,msg,rate_limit=10):
        reasons=[]
        if self.peer(msg.from_node)["status"]=="quarantined": reasons.append("peer_quarantined")
        if msg.expired(): reasons.append("message_expired")
        if not msg.verify_signature(): reasons.append("bad_signature")
        if self.nonce_seen(msg): reasons.append("replay_nonce")
        if not self.rate_ok(msg.from_node,rate_limit): reasons.append("rate_limit_exceeded")
        ok=not reasons; status="received" if ok else "rejected"
        self.conn.execute("INSERT OR REPLACE INTO inbox VALUES(?,?,?,?,?,?,?,?,?,?,?)",(msg.msg_id,msg.ts,msg.from_node,msg.to_node,msg.kind,msg.nonce,msg.ttl_seconds,msg.signature,1 if ok else 0,status,json.dumps(msg.payload)))
        if ok: self.remember_nonce(msg)
        else:
            sev="critical" if "bad_signature" in reasons or "replay_nonce" in reasons else "high"
            self.conflict(msg.from_node,msg.msg_id,"message_rejected",sev,{"reasons":reasons})
            self.penalize(msg.from_node,0.15 if sev=="critical" else 0.05,";".join(reasons))
        self.receipt("inbox_received",msg.msg_id,{"ok":ok,"reasons":reasons})
        self.conn.commit()
        return {"msg_id":msg.msg_id,"verified":ok,"status":status,"reasons":reasons}
    def mark_sent(self,msg_id):
        self.conn.execute("UPDATE outbox SET status='sent' WHERE msg_id=?",(msg_id,)); self.conn.commit()
    def conflict(self,source,subject,kind,severity,details):
        self.conn.execute("INSERT INTO conflicts(ts,source_node,subject,kind,severity,status,details_json) VALUES(?,?,?,?,?,?,?)",(time.time(),source,subject,kind,severity,"open",json.dumps(details)))
        self.receipt("conflict",subject,{"source":source,"kind":kind,"severity":severity,"details":details})
    def nodes(self): return [dict(r) for r in self.conn.execute("SELECT node_id,node_type,trust_score,status FROM nodes ORDER BY node_id")]
    def outbox(self,status=None):
        rows=self.conn.execute("SELECT * FROM outbox WHERE status=? ORDER BY ts",(status,)) if status else self.conn.execute("SELECT * FROM outbox ORDER BY ts")
        return [dict(r) for r in rows]
    def conflicts(self): return [dict(r) for r in self.conn.execute("SELECT source_node,subject,kind,severity,status,details_json FROM conflicts ORDER BY id")]
    def stats(self):
        return {"node_id":self.node_id,"nodes":self.conn.execute("SELECT COUNT(*) n FROM nodes").fetchone()["n"],"inbox":self.conn.execute("SELECT COUNT(*) n FROM inbox").fetchone()["n"],"outbox":self.conn.execute("SELECT COUNT(*) n FROM outbox").fetchone()["n"],"seen_nonces":self.conn.execute("SELECT COUNT(*) n FROM seen_nonces").fetchone()["n"],"conflicts":self.conn.execute("SELECT COUNT(*) n FROM conflicts").fetchone()["n"],"ledger":self.verify_ledger(),"db_integrity":self.conn.execute("PRAGMA integrity_check").fetchone()[0]}
    def bundle(self,out):
        out=Path(out)
        with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
            for table in ["nodes","inbox","outbox","seen_nonces","rate_limits","conflicts","ledger"]:
                rows=[dict(r) for r in self.conn.execute(f"SELECT * FROM {table} ORDER BY 1")]
                z.writestr(f"{table}.json",json.dumps(rows,indent=2,default=str))
            z.writestr("manifest.json",json.dumps({"stats":self.stats(),"created":time.time()},indent=2))
        return {"bundle":str(out),"exists":out.exists()}

class P2PRuntime:
    def __init__(self,store): self.store=store
    def add_peer(self,node): self.store.register_node(node)
    def send(self,to_node,kind,payload,ttl=300):
        msg=P2PMessage.create(self.store.node_id,to_node,kind,payload,ttl); self.store.queue_outbox(msg); return msg
    def deliver_to(self,other,msg_id):
        row=self.store.conn.execute("SELECT * FROM outbox WHERE msg_id=?",(msg_id,)).fetchone()
        if not row: return {"delivered":False}
        msg=P2PMessage.from_row(row); res=other.receive(msg)
        if res["verified"]: self.store.mark_sent(msg_id)
        return {"delivered":res["verified"],"result":res}
