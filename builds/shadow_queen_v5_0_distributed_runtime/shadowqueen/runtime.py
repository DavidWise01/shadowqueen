
import json,hashlib,sqlite3,time,zipfile
from pathlib import Path
def digest(o): return hashlib.sha256(json.dumps(o,sort_keys=True,default=str).encode()).hexdigest()
class Node:
    def __init__(self,path="runtime.db",node="office:north",region="local"):
        self.node=node; self.region=region
        self.conn=sqlite3.connect(Path(path)); self.conn.row_factory=sqlite3.Row
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS self(id TEXT PRIMARY KEY,region TEXT,status TEXT,last_seen REAL,key TEXT);
        CREATE TABLE IF NOT EXISTS peers(id TEXT PRIMARY KEY,region TEXT,status TEXT,last_seen REAL,endpoint TEXT,trust REAL);
        CREATE TABLE IF NOT EXISTS inbox(id TEXT PRIMARY KEY,src TEXT,kind TEXT,status TEXT,payload TEXT,hash TEXT);
        CREATE TABLE IF NOT EXISTS outbox(id TEXT PRIMARY KEY,dst TEXT,kind TEXT,status TEXT,payload TEXT,hash TEXT,attempts INTEGER);
        CREATE TABLE IF NOT EXISTS heartbeats(id INTEGER PRIMARY KEY,peer TEXT,status TEXT,details TEXT);
        CREATE TABLE IF NOT EXISTS repl(id INTEGER PRIMARY KEY,obj_type TEXT,obj_id TEXT,dst TEXT,status TEXT,details TEXT);
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,type TEXT,subject TEXT,details TEXT);
        CREATE TABLE IF NOT EXISTS ledger(seq INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT,subject TEXT,payload_hash TEXT,prev_hash TEXT,entry_hash TEXT);
        """); self.conn.commit(); self.register()
    def key(self): return digest({"node":self.node,"region":self.region})[:32]
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
    def event(self,t,s,d=None):
        self.conn.execute("INSERT INTO events(type,subject,details) VALUES(?,?,?)",(t,s,json.dumps(d or {})))
        self.receipt("event",s,{"type":t,"details":d or {}})
    def register(self):
        self.conn.execute("INSERT OR REPLACE INTO self VALUES(?,?,?,?,?)",(self.node,self.region,"online",time.time(),self.key()))
        self.receipt("node_registered",self.node,{"region":self.region})
    def add_peer(self,peer,region="remote",endpoint="",trust=75):
        self.conn.execute("INSERT OR REPLACE INTO peers VALUES(?,?,?,?,?,?)",(peer,region,"known",time.time(),endpoint,float(trust)))
        self.event("peer_added",peer,{"region":region})
    def discover(self,nodes):
        found=[]
        for n in nodes:
            if n.node!=self.node:
                self.add_peer(n.node,n.region,"local://"+n.node,75); found.append(n.node)
        self.event("discovery",self.node,{"found":found}); return found
    def envelope(self,dst,kind,payload):
        base={"src":self.node,"dst":dst,"kind":kind,"payload":payload,"ts":time.time()}
        h=digest(base); sig=digest({"key":self.key(),"hash":h})
        return {"id":"msg:"+h[:16],"src":self.node,"dst":dst,"kind":kind,"payload":payload,"ts":base["ts"],"hash":h,"sig":sig}
    def queue(self,dst,kind,payload):
        e=self.envelope(dst,kind,payload)
        self.conn.execute("INSERT OR REPLACE INTO outbox VALUES(?,?,?,?,?,?,?)",(e["id"],dst,kind,"queued",json.dumps(payload),e["hash"],0))
        self.receipt("queued",e["id"],e); return e
    def receive(self,e):
        if e["dst"] not in (self.node,"*"): return {"accepted":False,"reason":"wrong_dst"}
        calc=digest({"src":e["src"],"dst":e["dst"],"kind":e["kind"],"payload":e["payload"],"ts":e["ts"]})
        if calc!=e["hash"]: return {"accepted":False,"reason":"bad_hash"}
        self.conn.execute("INSERT OR REPLACE INTO inbox VALUES(?,?,?,?,?,?)",(e["id"],e["src"],e["kind"],"accepted",json.dumps(e["payload"]),e["hash"]))
        self.add_peer(e["src"],"discovered","",50)
        self.receipt("received",e["id"],e); self.conn.commit()
        return {"accepted":True,"message":e["id"]}
    def deliver(self,other,e):
        r=other.receive(e); status="delivered" if r.get("accepted") else "failed"
        self.conn.execute("UPDATE outbox SET status=?,attempts=attempts+1 WHERE id=?",(status,e["id"]))
        self.receipt("delivery",e["id"],{"dst":other.node,"status":status}); self.conn.commit()
        return {"message":e["id"],"dst":other.node,"status":status}
    def heartbeat(self,other):
        e=self.queue(other.node,"heartbeat",{"node":self.node,"ledger":self.verify_ledger()["head"]})
        r=self.deliver(other,e)
        self.conn.execute("INSERT INTO heartbeats(peer,status,details) VALUES(?,?,?)",(other.node,r["status"],json.dumps(r)))
        self.conn.commit(); return r
    def replicate(self,other,obj_type,obj_id,payload):
        e=self.queue(other.node,"replicate",{"object_type":obj_type,"object_id":obj_id,"payload":payload})
        r=self.deliver(other,e)
        self.conn.execute("INSERT INTO repl(obj_type,obj_id,dst,status,details) VALUES(?,?,?,?,?)",(obj_type,obj_id,other.node,r["status"],json.dumps(r)))
        self.conn.commit(); return r
    def status(self):
        return {"node":self.node,"region":self.region,"peers":self.conn.execute("SELECT COUNT(*) n FROM peers").fetchone()["n"],"inbox":self.conn.execute("SELECT COUNT(*) n FROM inbox").fetchone()["n"],"outbox":self.conn.execute("SELECT COUNT(*) n FROM outbox").fetchone()["n"],"heartbeats":self.conn.execute("SELECT COUNT(*) n FROM heartbeats").fetchone()["n"],"replications":self.conn.execute("SELECT COUNT(*) n FROM repl").fetchone()["n"],"ledger":self.verify_ledger(),"db_integrity":self.conn.execute("PRAGMA integrity_check").fetchone()[0]}
    def bundle(self,out):
        out=Path(out)
        with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
            for t in ["self","peers","inbox","outbox","heartbeats","repl","events","ledger"]:
                z.writestr(f"{t}.json",json.dumps([dict(r) for r in self.conn.execute(f"SELECT * FROM {t} ORDER BY 1")],indent=2,default=str))
            z.writestr("mesh_status.json",json.dumps(self.status(),indent=2))
            z.writestr("manifest.json",json.dumps({"status":self.status(),"created":time.time()},indent=2))
        return {"bundle":str(out),"exists":out.exists()}
def demo(td):
    n=Node(Path(td)/"north.db","office:north","MN"); s=Node(Path(td)/"south.db","office:south","IA"); e=Node(Path(td)/"east.db","office:east","WI"); w=Node(Path(td)/"west.db","office:west","ND")
    nodes=[n,s,e,w]
    for x in nodes: x.discover(nodes)
    hb=n.heartbeat(s); rep=n.replicate(e,"credential","credential:C-1",{"status":"active"})
    b=[n.deliver(p,n.queue(p.node,"mesh_notice",{"runtime":"online"})) for p in [s,e,w]]
    return {"north":n.status(),"south":s.status(),"east":e.status(),"west":w.status(),"heartbeat":hb,"replication":rep,"broadcast":b}
