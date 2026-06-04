
import json, hashlib, sqlite3, time, zipfile
from pathlib import Path

def digest(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()

class Store:
    def __init__(self, path="graph.db", office="north"):
        self.office=office
        self.conn=sqlite3.connect(Path(path))
        self.conn.row_factory=sqlite3.Row
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS nodes(id TEXT PRIMARY KEY,type TEXT,office TEXT,hash TEXT,version INTEGER,attrs TEXT);
        CREATE TABLE IF NOT EXISTS edges(id INTEGER PRIMARY KEY,src TEXT,dst TEXT,rel TEXT,office TEXT,hash TEXT,version INTEGER,attrs TEXT);
        CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY,office TEXT,type TEXT,hash TEXT,ts REAL,payload TEXT,verified INTEGER,applied INTEGER);
        CREATE TABLE IF NOT EXISTS outbox(id INTEGER PRIMARY KEY,event_id TEXT,target TEXT,status TEXT);
        CREATE TABLE IF NOT EXISTS inbox(id INTEGER PRIMARY KEY,event_id TEXT,source TEXT,status TEXT);
        CREATE TABLE IF NOT EXISTS conflicts(id INTEGER PRIMARY KEY,ts REAL,subject TEXT,kind TEXT,severity TEXT,details TEXT);
        CREATE TABLE IF NOT EXISTS audits(id INTEGER PRIMARY KEY,ts REAL,auditor TEXT,result TEXT,details TEXT);
        CREATE TABLE IF NOT EXISTS ledger(seq INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT,subject TEXT,payload_hash TEXT,prev_hash TEXT,entry_hash TEXT);
        """)
        self.conn.commit()

    def last_hash(self):
        r=self.conn.execute("SELECT entry_hash FROM ledger ORDER BY seq DESC LIMIT 1").fetchone()
        return r["entry_hash"] if r else "GENESIS"

    def receipt(self, kind, subject, payload):
        prev=self.last_hash()
        ph=digest(payload)
        eh=digest({"kind":kind,"subject":subject,"payload_hash":ph,"prev_hash":prev})
        self.conn.execute("INSERT INTO ledger(kind,subject,payload_hash,prev_hash,entry_hash) VALUES(?,?,?,?,?)",(kind,subject,ph,prev,eh))
        self.conn.commit()

    def verify_ledger(self):
        prev="GENESIS"; n=0
        for r in self.conn.execute("SELECT seq,kind,subject,payload_hash,prev_hash,entry_hash FROM ledger ORDER BY seq"):
            exp=digest({"kind":r["kind"],"subject":r["subject"],"payload_hash":r["payload_hash"],"prev_hash":prev})
            if r["prev_hash"]!=prev: return {"ok":False,"seq":r["seq"],"reason":"prev_hash_mismatch"}
            if r["entry_hash"]!=exp: return {"ok":False,"seq":r["seq"],"reason":"entry_hash_mismatch"}
            prev=r["entry_hash"]; n+=1
        return {"ok":True,"entries":n,"head":prev}

    def node_id(self, typ, key):
        return f"{typ}:{digest({'type':typ,'key':key})[:16]}"

    def event(self, typ, payload):
        ts=time.time()
        base={"office":self.office,"type":typ,"payload":payload,"ts":ts}
        eid=digest(base)
        eh=digest({**base,"event_id":eid})
        self.conn.execute("INSERT OR IGNORE INTO events VALUES(?,?,?,?,?,?,?,?)",(eid,self.office,typ,eh,ts,json.dumps(payload),1,0))
        self.receipt("event", eid, {"type":typ})
        return eid

    def add_node(self, typ, key, attrs, targets=None, version=1):
        nid=self.node_id(typ,key)
        nh=digest({"id":nid,"type":typ,"attrs":attrs,"version":version})
        payload={"node":{"id":nid,"type":typ,"office":self.office,"hash":nh,"version":version,"attrs":attrs}}
        eid=self.event("node", payload)
        self.apply(eid)
        for t in targets or []:
            self.conn.execute("INSERT INTO outbox(event_id,target,status) VALUES(?,?,?)",(eid,t,"queued"))
        self.conn.commit()
        return eid

    def add_edge(self, src, typ, key, rel, attrs=None, targets=None, version=1):
        dst=self.node_id(typ,key)
        nh=digest({"id":dst,"type":typ,"attrs":attrs or {},"version":version})
        edge={"src":src,"dst":dst,"rel":rel,"office":self.office,"hash":digest({"src":src,"dst":dst,"rel":rel,"attrs":attrs or {}, "version":version}),"version":version,"attrs":{}}
        payload={"node":{"id":dst,"type":typ,"office":self.office,"hash":nh,"version":version,"attrs":attrs or {}},"edge":edge}
        eid=self.event("node_edge", payload)
        self.apply(eid)
        for t in targets or []:
            self.conn.execute("INSERT INTO outbox(event_id,target,status) VALUES(?,?,?)",(eid,t,"queued"))
        self.conn.commit()
        return eid

    def get_event(self, eid):
        r=self.conn.execute("SELECT * FROM events WHERE id=?",(eid,)).fetchone()
        return dict(r) if r else None

    def apply(self, eid):
        ev=self.get_event(eid)
        if not ev: return {"applied":False,"reason":"missing"}
        payload=json.loads(ev["payload"])
        if ev["type"] in ("node","node_edge"):
            n=payload["node"]
            cur=self.conn.execute("SELECT version FROM nodes WHERE id=?",(n["id"],)).fetchone()
            if cur and cur["version"]>n["version"]:
                self.conflict(n["id"],"stale_node_version","medium",n); return {"applied":False,"reason":"stale"}
            self.conn.execute("INSERT OR REPLACE INTO nodes VALUES(?,?,?,?,?,?)",(n["id"],n["type"],n["office"],n["hash"],n["version"],json.dumps(n["attrs"])))
        if ev["type"]=="node_edge":
            e=payload["edge"]
            self.conn.execute("INSERT INTO edges(src,dst,rel,office,hash,version,attrs) VALUES(?,?,?,?,?,?,?)",(e["src"],e["dst"],e["rel"],e["office"],e["hash"],e["version"],json.dumps(e["attrs"])))
        self.conn.execute("UPDATE events SET applied=1 WHERE id=?",(eid,))
        self.receipt("apply", eid, payload)
        self.conn.commit()
        return {"applied":True}

    def receive(self, evrow, source):
        if self.conn.execute("SELECT 1 FROM events WHERE id=?",(evrow["id"],)).fetchone():
            self.conn.execute("INSERT INTO inbox(event_id,source,status) VALUES(?,?,?)",(evrow["id"],source,"duplicate"))
            self.conn.commit(); return {"accepted":False,"status":"duplicate"}
        self.conn.execute("INSERT INTO events VALUES(?,?,?,?,?,?,?,?)",(evrow["id"],evrow["office"],evrow["type"],evrow["hash"],evrow["ts"],evrow["payload"],evrow["verified"],0))
        res=self.apply(evrow["id"])
        self.conn.execute("INSERT INTO inbox(event_id,source,status) VALUES(?,?,?)",(evrow["id"],source,"accepted"))
        self.conn.commit(); return {"accepted":True,"applied":res}

    def replay(self, peers):
        out=[]
        for row in self.conn.execute("SELECT * FROM outbox WHERE status='queued' ORDER BY id"):
            peer=peers.get(row["target"])
            if not peer: continue
            ev=self.get_event(row["event_id"])
            res=peer.receive(ev,self.office)
            self.conn.execute("UPDATE outbox SET status=? WHERE id=?",("sent" if res.get("accepted") else res.get("status","failed"),row["id"]))
            out.append(res)
        self.conn.commit()
        return out

    def conflict(self, subject, kind, severity, details):
        self.conn.execute("INSERT INTO conflicts(ts,subject,kind,severity,details) VALUES(?,?,?,?,?)",(time.time(),subject,kind,severity,json.dumps(details,default=str)))
        self.receipt("conflict", subject, {"kind":kind,"severity":severity})

    def duplicate_scan(self):
        groups={}
        for n in self.nodes():
            a=json.loads(n["attrs"])
            key=digest({"name":a.get("name","").lower().strip(),"dob":a.get("dob",""),"domain":a.get("domain","")})
            groups.setdefault(key,[]).append(n["id"])
        found=[]
        for k,ids in groups.items():
            if len(ids)>1:
                self.conflict(k,"possible_duplicate_identity","high",{"nodes":ids}); found.append({"key":k,"nodes":ids})
        self.conn.commit()
        return found

    def nodes(self): return [dict(r) for r in self.conn.execute("SELECT * FROM nodes ORDER BY id")]
    def edges(self): return [dict(r) for r in self.conn.execute("SELECT * FROM edges ORDER BY id")]

    def audit(self, peers, auditor="auditor"):
        ln={n["id"]:n["hash"] for n in self.nodes()}
        le={e["hash"] for e in self.edges()}
        report={}
        result="pass"
        for p in peers:
            pn={n["id"]:n["hash"] for n in p.nodes()}
            pe={e["hash"] for e in p.edges()}
            drift={
                "missing_nodes_remote": sorted([x for x in ln if x not in pn]),
                "missing_nodes_local": sorted([x for x in pn if x not in ln]),
                "node_hash_mismatch": sorted([x for x in ln if x in pn and ln[x]!=pn[x]]),
                "missing_edges_remote": len(le-pe),
                "missing_edges_local": len(pe-le)
            }
            report[p.office]=drift
            if any(drift[k] for k in drift): result="warning"
        self.conn.execute("INSERT INTO audits(ts,auditor,result,details) VALUES(?,?,?,?)",(time.time(),auditor,result,json.dumps(report)))
        self.receipt("audit", auditor, {"result":result})
        self.conn.commit()
        return {"result":result,"report":report}

    def stats(self):
        return {
            "office":self.office,
            "nodes":self.conn.execute("SELECT COUNT(*) n FROM nodes").fetchone()["n"],
            "edges":self.conn.execute("SELECT COUNT(*) n FROM edges").fetchone()["n"],
            "events":self.conn.execute("SELECT COUNT(*) n FROM events").fetchone()["n"],
            "conflicts":self.conn.execute("SELECT COUNT(*) n FROM conflicts").fetchone()["n"],
            "audits":self.conn.execute("SELECT COUNT(*) n FROM audits").fetchone()["n"],
            "ledger":self.verify_ledger(),
            "db_integrity":self.conn.execute("PRAGMA integrity_check").fetchone()[0]
        }

    def bundle(self,out):
        out=Path(out)
        with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
            for t in ["nodes","edges","events","outbox","inbox","conflicts","audits","ledger"]:
                z.writestr(f"{t}.json",json.dumps([dict(r) for r in self.conn.execute(f"SELECT * FROM {t} ORDER BY 1")],indent=2,default=str))
            z.writestr("manifest.json",json.dumps({"stats":self.stats(),"created":time.time()},indent=2))
        return {"bundle":str(out),"exists":out.exists()}
