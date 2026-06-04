
import json,sqlite3,time,hashlib,zipfile
from pathlib import Path
def digest(o): return hashlib.sha256(json.dumps(o,sort_keys=True,default=str).encode()).hexdigest()
class Node:
    def __init__(self,path="cluster.db",node="office:north"):
        self.node=node; self.conn=sqlite3.connect(Path(path)); self.conn.row_factory=sqlite3.Row
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS kv(k TEXT PRIMARY KEY,v TEXT,ver INTEGER,owner TEXT,h TEXT);
        CREATE TABLE IF NOT EXISTS peers(node TEXT PRIMARY KEY,status TEXT,state_hash TEXT);
        CREATE TABLE IF NOT EXISTS log(id INTEGER PRIMARY KEY,op TEXT,k TEXT,ver INTEGER,h TEXT);
        CREATE TABLE IF NOT EXISTS snapshots(id TEXT PRIMARY KEY,state_hash TEXT,payload TEXT);
        CREATE TABLE IF NOT EXISTS syncs(id INTEGER PRIMARY KEY,peer TEXT,status TEXT,details TEXT);
        CREATE TABLE IF NOT EXISTS divergence(id INTEGER PRIMARY KEY,peer TEXT,kind TEXT,status TEXT,details TEXT);
        CREATE TABLE IF NOT EXISTS recovery(id INTEGER PRIMARY KEY,kind TEXT,status TEXT,details TEXT);
        CREATE TABLE IF NOT EXISTS ledger(seq INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT,subject TEXT,payload_hash TEXT,prev_hash TEXT,entry_hash TEXT);
        """); self.conn.commit(); self.receipt("node_opened",self.node,{"node":self.node})
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
    def put(self,k,v,ver=None):
        cur=self.conn.execute("SELECT ver FROM kv WHERE k=?",(k,)).fetchone()
        ver=ver if ver is not None else ((cur["ver"]+1) if cur else 1)
        val=json.dumps(v,sort_keys=True); h=digest({"k":k,"v":v,"ver":ver,"owner":self.node})
        self.conn.execute("INSERT OR REPLACE INTO kv VALUES(?,?,?,?,?)",(k,val,ver,self.node,h))
        self.conn.execute("INSERT INTO log(op,k,ver,h) VALUES(?,?,?,?)",("put",k,ver,h))
        self.receipt("put",k,{"ver":ver,"h":h}); self.conn.commit()
    def state(self): return [dict(r) for r in self.conn.execute("SELECT * FROM kv ORDER BY k")]
    def state_hash(self): return digest([{"k":r["k"],"v":r["v"],"ver":r["ver"],"h":r["h"]} for r in self.conn.execute("SELECT * FROM kv ORDER BY k")])
    def add_peer(self,p):
        self.conn.execute("INSERT OR REPLACE INTO peers VALUES(?,?,?)",(p.node,"known",p.state_hash()))
        self.receipt("peer",p.node,{"state_hash":p.state_hash()}); self.conn.commit()
    def snapshot(self,label=""):
        payload=self.state(); sh=self.state_hash(); sid="snapshot:"+digest({"node":self.node,"sh":sh,"label":label,"t":time.time()})[:16]
        self.conn.execute("INSERT INTO snapshots VALUES(?,?,?)",(sid,sh,json.dumps(payload)))
        self.receipt("snapshot",sid,{"state_hash":sh}); self.conn.commit()
        return {"snapshot":sid,"state_hash":sh,"items":len(payload)}
    def apply_row(self,row):
        local=self.conn.execute("SELECT * FROM kv WHERE k=?",(row["k"],)).fetchone()
        if local and local["ver"]>row["ver"]: return {"applied":False,"reason":"local_newer"}
        if local and local["ver"]==row["ver"] and local["h"]!=row["h"]:
            self.conn.execute("INSERT INTO divergence(peer,kind,status,details) VALUES(?,?,?,?)",(row["owner"],"hash_conflict","open",json.dumps({"key":row["k"],"local":local["h"],"remote":row["h"]})))
            return {"applied":False,"reason":"conflict"}
        self.conn.execute("INSERT OR REPLACE INTO kv VALUES(?,?,?,?,?)",(row["k"],row["v"],row["ver"],row["owner"],row["h"]))
        return {"applied":True}
    def sync_to(self,p):
        sent=applied=conflicts=0
        for row in self.state():
            res=p.apply_row(row); sent+=1
            if res["applied"]: applied+=1
            elif res["reason"]=="conflict": conflicts+=1
        p.conn.commit()
        status="conflict" if conflicts else "ok"
        detail={"sent":sent,"applied":applied,"conflicts":conflicts}
        self.conn.execute("INSERT INTO syncs(peer,status,details) VALUES(?,?,?)",(p.node,status,json.dumps(detail)))
        p.conn.execute("INSERT INTO syncs(peer,status,details) VALUES(?,?,?)",(self.node,status,json.dumps(detail)))
        self.receipt("sync_out",p.node,detail); p.receipt("sync_in",self.node,detail)
        self.conn.commit(); p.conn.commit()
        return {"peer":p.node,"status":status,**detail}
    def compare(self,p):
        a={r["k"]:r for r in self.state()}; b={r["k"]:r for r in p.state()}
        detail={"missing_remote":[k for k in a if k not in b],"missing_local":[k for k in b if k not in a],"mismatch":[k for k in a if k in b and a[k]["h"]!=b[k]["h"]]}
        status="diverged" if any(detail.values()) else "converged"
        self.conn.execute("INSERT INTO divergence(peer,kind,status,details) VALUES(?,?,?,?)",(p.node,"compare",status,json.dumps(detail)))
        self.receipt("compare",p.node,{"status":status}); self.conn.commit()
        return {"peer":p.node,"status":status,"detail":detail}
    def restore_snapshot(self,sid):
        r=self.conn.execute("SELECT * FROM snapshots WHERE id=?",(sid,)).fetchone()
        if not r: return {"restored":False}
        self.conn.execute("DELETE FROM kv")
        rows=json.loads(r["payload"])
        for row in rows: self.conn.execute("INSERT INTO kv VALUES(?,?,?,?,?)",(row["k"],row["v"],row["ver"],row["owner"],row["h"]))
        self.conn.execute("INSERT INTO recovery(kind,status,details) VALUES(?,?,?)",("restore_snapshot","ok",json.dumps({"snapshot":sid,"items":len(rows)})))
        self.receipt("restore",sid,{"items":len(rows)}); self.conn.commit()
        return {"restored":True,"items":len(rows)}
    def recover_from_peer(self,p):
        self.conn.execute("DELETE FROM kv"); count=0
        for row in p.state(): self.apply_row(row); count+=1
        self.conn.execute("INSERT INTO recovery(kind,status,details) VALUES(?,?,?)",("recover_from_peer","ok",json.dumps({"peer":p.node,"items":count})))
        self.receipt("recover_peer",p.node,{"items":count}); self.conn.commit()
        return {"recovered":True,"items":count,"state_hash":self.state_hash()}
    def stats(self):
        return {"node":self.node,"items":self.conn.execute("SELECT COUNT(*) n FROM kv").fetchone()["n"],"peers":self.conn.execute("SELECT COUNT(*) n FROM peers").fetchone()["n"],"changes":self.conn.execute("SELECT COUNT(*) n FROM log").fetchone()["n"],"snapshots":self.conn.execute("SELECT COUNT(*) n FROM snapshots").fetchone()["n"],"syncs":self.conn.execute("SELECT COUNT(*) n FROM syncs").fetchone()["n"],"divergence_records":self.conn.execute("SELECT COUNT(*) n FROM divergence").fetchone()["n"],"recoveries":self.conn.execute("SELECT COUNT(*) n FROM recovery").fetchone()["n"],"state_hash":self.state_hash(),"ledger":self.verify_ledger(),"db_integrity":self.conn.execute("PRAGMA integrity_check").fetchone()[0]}
    def bundle(self,out):
        out=Path(out)
        with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
            for t in ["kv","peers","log","snapshots","syncs","divergence","recovery","ledger"]:
                z.writestr(f"{t}.json",json.dumps([dict(r) for r in self.conn.execute(f"SELECT * FROM {t} ORDER BY 1")],indent=2))
            z.writestr("cluster_status.json",json.dumps(self.stats(),indent=2))
        return {"bundle":str(out),"exists":out.exists()}
def seed_demo(td):
    n=Node(Path(td)/"north.db","office:north"); s=Node(Path(td)/"south.db","office:south"); e=Node(Path(td)/"east.db","office:east"); w=Node(Path(td)/"west.db","office:west")
    nodes=[n,s,e,w]
    for x in nodes:
        for p in nodes:
            if p.node!=x.node: x.add_peer(p)
    for i in range(20): n.put(f"credential:{i}",{"owner":f"citizen:{i%5}","status":"active"})
    snap=n.snapshot("before_sync")
    s1=n.sync_to(s); s2=n.sync_to(e)
    w.put("credential:0",{"owner":"citizen:0","status":"revoked"},ver=1)
    conflict=n.sync_to(w); compare=n.compare(w)
    badsnap=w.snapshot("bad_state"); w.restore_snapshot(badsnap["snapshot"])
    rec=w.recover_from_peer(n); final=n.sync_to(w)
    return {"north":n.stats(),"south":s.stats(),"east":e.stats(),"west":w.stats(),"snapshot":snap,"syncs":[s1,s2,conflict,final],"compare":compare,"recovery":rec}
