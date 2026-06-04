
import json, hashlib, sqlite3, time, zipfile
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Any

def digest(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,default=str).encode()).hexdigest()

@dataclass(frozen=True)
class PeerNode:
    node_id:str
    node_type:str="office"
    trust_score:float=0.5
    status:str="active"
    @classmethod
    def from_dict(cls,d):
        return cls(str(d["node_id"]),str(d.get("node_type","office")),float(d.get("trust_score",0.5)),str(d.get("status","active")))
    def fingerprint(self):
        return digest(self.__dict__)

@dataclass(frozen=True)
class P2PMessage:
    msg_id:str
    from_node:str
    to_node:str
    kind:str
    payload:Dict[str,Any]=field(default_factory=dict)
    ts:float=0.0
    signature:str=""
    @classmethod
    def create(cls,from_node,to_node,kind,payload):
        ts=time.time()
        base={"from_node":from_node,"to_node":to_node,"kind":kind,"payload":payload,"ts":ts}
        msg_id=digest(base)
        sig=digest({"msg_id":msg_id,"from_node":from_node,"payload":payload})
        return cls(msg_id,from_node,to_node,kind,payload,ts,sig)
    @classmethod
    def from_row(cls,row):
        return cls(row["msg_id"],row["from_node"],row["to_node"],row["kind"],json.loads(row["payload_json"]),row["ts"],row["signature"])
    def verify(self):
        return self.signature==digest({"msg_id":self.msg_id,"from_node":self.from_node,"payload":self.payload})

class Store:
    def __init__(self,path="p2p.db",node_id="queen"):
        self.node_id=node_id
        self.conn=sqlite3.connect(Path(path)); self.conn.row_factory=sqlite3.Row
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS nodes(node_id TEXT PRIMARY KEY,node_type TEXT,trust_score REAL,status TEXT,fingerprint TEXT,updated_ts REAL);
        CREATE TABLE IF NOT EXISTS inbox(msg_id TEXT PRIMARY KEY,ts REAL,from_node TEXT,to_node TEXT,kind TEXT,signature TEXT,verified INTEGER,status TEXT,payload_json TEXT);
        CREATE TABLE IF NOT EXISTS outbox(msg_id TEXT PRIMARY KEY,ts REAL,from_node TEXT,to_node TEXT,kind TEXT,signature TEXT,status TEXT,payload_json TEXT);
        CREATE TABLE IF NOT EXISTS conflicts(id INTEGER PRIMARY KEY,ts REAL,source_node TEXT,subject TEXT,kind TEXT,severity TEXT,status TEXT,details_json TEXT);
        CREATE TABLE IF NOT EXISTS heartbeats(id INTEGER PRIMARY KEY,ts REAL,node_id TEXT,status TEXT,details_json TEXT);
        CREATE TABLE IF NOT EXISTS replay_log(id INTEGER PRIMARY KEY,ts REAL,msg_id TEXT,result TEXT,details_json TEXT);
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
        self.receipt("node_registered",node.node_id,{"fingerprint":fp,"trust":node.trust_score})
    def heartbeat(self,status="ok",details=None):
        self.conn.execute("INSERT INTO heartbeats(ts,node_id,status,details_json) VALUES(?,?,?,?)",(time.time(),self.node_id,status,json.dumps(details or {})))
        self.receipt("heartbeat",self.node_id,{"status":status,"details":details or {}})
    def queue_outbox(self,msg):
        self.conn.execute("INSERT OR REPLACE INTO outbox VALUES(?,?,?,?,?,?,?,?)",(msg.msg_id,msg.ts,msg.from_node,msg.to_node,msg.kind,msg.signature,"queued",json.dumps(msg.payload)))
        self.receipt("outbox_queued",msg.msg_id,msg.__dict__)
        self.conn.commit()
    def receive(self,msg):
        verified=1 if msg.verify() else 0
        status="received" if verified else "rejected"
        self.conn.execute("INSERT OR REPLACE INTO inbox VALUES(?,?,?,?,?,?,?,?,?)",(msg.msg_id,msg.ts,msg.from_node,msg.to_node,msg.kind,msg.signature,verified,status,json.dumps(msg.payload)))
        self.receipt("inbox_received",msg.msg_id,{"from":msg.from_node,"kind":msg.kind,"verified":verified})
        if not verified:
            self.conflict(msg.from_node,msg.msg_id,"bad_signature","high",{"payload":msg.payload})
        self.conn.commit()
        return {"msg_id":msg.msg_id,"verified":bool(verified),"status":status}
    def mark_sent(self,msg_id):
        self.conn.execute("UPDATE outbox SET status='sent' WHERE msg_id=?",(msg_id,)); self.conn.commit()
    def conflict(self,source,subject,kind,severity,details):
        self.conn.execute("INSERT INTO conflicts(ts,source_node,subject,kind,severity,status,details_json) VALUES(?,?,?,?,?,?,?)",(time.time(),source,subject,kind,severity,"open",json.dumps(details,default=str)))
        self.receipt("conflict",subject,{"source":source,"kind":kind,"severity":severity,"details":details})
    def nodes(self): return [dict(r) for r in self.conn.execute("SELECT node_id,node_type,trust_score,status,fingerprint FROM nodes ORDER BY node_id")]
    def outbox(self,status=None):
        if status: rows=self.conn.execute("SELECT * FROM outbox WHERE status=? ORDER BY ts",(status,))
        else: rows=self.conn.execute("SELECT * FROM outbox ORDER BY ts")
        return [dict(r) for r in rows]
    def inbox(self): return [dict(r) for r in self.conn.execute("SELECT * FROM inbox ORDER BY ts")]
    def conflicts(self): return [dict(r) for r in self.conn.execute("SELECT source_node,subject,kind,severity,status,details_json FROM conflicts ORDER BY id")]
    def stats(self):
        return {"node_id":self.node_id,"nodes":self.conn.execute("SELECT COUNT(*) n FROM nodes").fetchone()["n"],"inbox":self.conn.execute("SELECT COUNT(*) n FROM inbox").fetchone()["n"],"outbox":self.conn.execute("SELECT COUNT(*) n FROM outbox").fetchone()["n"],"conflicts":self.conn.execute("SELECT COUNT(*) n FROM conflicts").fetchone()["n"],"heartbeats":self.conn.execute("SELECT COUNT(*) n FROM heartbeats").fetchone()["n"],"ledger":self.verify_ledger(),"db_integrity":self.conn.execute("PRAGMA integrity_check").fetchone()[0]}
    def bundle(self,out):
        out=Path(out)
        with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
            for table in ["nodes","inbox","outbox","conflicts","heartbeats","replay_log","ledger"]:
                rows=[dict(r) for r in self.conn.execute(f"SELECT * FROM {table} ORDER BY 1")]
                z.writestr(f"{table}.json",json.dumps(rows,indent=2,default=str))
            z.writestr("manifest.json",json.dumps({"stats":self.stats(),"created":time.time()},indent=2))
        return {"bundle":str(out),"exists":out.exists()}

class P2PRuntime:
    def __init__(self,store): self.store=store
    def add_peer(self,node): self.store.register_node(node)
    def send(self,to_node,kind,payload):
        msg=P2PMessage.create(self.store.node_id,to_node,kind,payload); self.store.queue_outbox(msg); return msg
    def deliver_to(self,other,msg_id):
        row=self.store.conn.execute("SELECT * FROM outbox WHERE msg_id=?",(msg_id,)).fetchone()
        if not row: return {"delivered":False,"reason":"missing_message"}
        msg=P2PMessage.from_row(row); res=other.receive(msg)
        if res["verified"]: self.store.mark_sent(msg_id)
        return {"delivered":res["verified"],"result":res}
    def replay_outbox(self,peers):
        peer_map={p.node_id:p for p in peers}; results=[]
        for row in self.store.outbox("queued"):
            target=peer_map.get(row["to_node"])
            if not target:
                self.store.conn.execute("INSERT INTO replay_log(ts,msg_id,result,details_json) VALUES(?,?,?,?)",(time.time(),row["msg_id"],"no_peer",json.dumps({"to":row["to_node"]})))
                continue
            res=self.deliver_to(target,row["msg_id"])
            self.store.conn.execute("INSERT INTO replay_log(ts,msg_id,result,details_json) VALUES(?,?,?,?)",(time.time(),row["msg_id"],"delivered" if res["delivered"] else "failed",json.dumps(res)))
            results.append(res)
        self.store.conn.commit(); return results
    def federated_trust_score(self):
        nodes=self.store.nodes()
        active=[n for n in nodes if n["status"]=="active"]
        avg=sum(float(n["trust_score"]) for n in active)/max(1,len(active))
        penalty=min(.5,.1*len(self.store.conflicts()))
        return {"score":round(max(0,avg-penalty),4),"active_nodes":len(active),"conflicts":len(self.store.conflicts())}
