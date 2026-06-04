
import json, hashlib, sqlite3, time, zipfile
from pathlib import Path
from dataclasses import dataclass
from collections import defaultdict

def digest(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,default=str).encode()).hexdigest()

@dataclass(frozen=True)
class IdentityNode:
    entity_id:str
    entity_type:str
    proof_hash:str
    trust_score:float=0.0
    @classmethod
    def from_dict(cls,d):
        et=str(d["entity_type"]).lower()
        if et not in {"carbon","silicon"}: raise ValueError("entity_type must be carbon or silicon")
        return cls(str(d["entity_id"]),et,str(d.get("proof_hash",d.get("identity_hash",""))),float(d.get("trust_score",0.0)))
    def fingerprint(self):
        return digest({"entity_id":self.entity_id,"entity_type":self.entity_type,"proof_hash":self.proof_hash})

@dataclass(frozen=True)
class TrustEdge:
    source_id:str
    target_id:str
    relation:str
    confidence:float=1.0
    @classmethod
    def from_dict(cls,d):
        return cls(str(d["source_id"]),str(d["target_id"]),str(d["relation"]),float(d.get("confidence",1.0)))

class Store:
    def __init__(self,path="fraud_graph.db"):
        self.conn=sqlite3.connect(Path(path)); self.conn.row_factory=sqlite3.Row
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS nodes(entity_id TEXT PRIMARY KEY,entity_type TEXT,proof_hash TEXT,trust_score REAL,fingerprint TEXT);
        CREATE TABLE IF NOT EXISTS edges(id INTEGER PRIMARY KEY,ts REAL,source_id TEXT,target_id TEXT,relation TEXT,confidence REAL);
        CREATE TABLE IF NOT EXISTS findings(id INTEGER PRIMARY KEY,ts REAL,kind TEXT,severity TEXT,subject TEXT,score REAL,details_json TEXT);
        CREATE TABLE IF NOT EXISTS ledger(seq INTEGER PRIMARY KEY AUTOINCREMENT,ts REAL,kind TEXT,subject TEXT,payload_hash TEXT,prev_hash TEXT,entry_hash TEXT);
        """); self.conn.commit()
    def last_hash(self):
        r=self.conn.execute("SELECT entry_hash FROM ledger ORDER BY seq DESC LIMIT 1").fetchone()
        return r["entry_hash"] if r else "GENESIS"
    def receipt(self,kind,subject,payload):
        prev=self.last_hash(); ph=digest(payload); eh=digest({"kind":kind,"subject":subject,"payload_hash":ph,"prev_hash":prev})
        self.conn.execute("INSERT INTO ledger(ts,kind,subject,payload_hash,prev_hash,entry_hash) VALUES(?,?,?,?,?,?)",(time.time(),kind,subject,ph,prev,eh)); self.conn.commit()
    def add_node(self,n):
        fp=n.fingerprint()
        self.conn.execute("INSERT OR REPLACE INTO nodes VALUES(?,?,?,?,?)",(n.entity_id,n.entity_type,n.proof_hash,n.trust_score,fp))
        self.receipt("node",n.entity_id,{"fp":fp,"trust":n.trust_score})
    def add_edge(self,e):
        self.conn.execute("INSERT INTO edges(ts,source_id,target_id,relation,confidence) VALUES(?,?,?,?,?)",(time.time(),e.source_id,e.target_id,e.relation,e.confidence))
        self.receipt("edge",f"{e.source_id}->{e.target_id}",{"relation":e.relation,"confidence":e.confidence})
    def finding(self,kind,severity,subject,score,details):
        self.conn.execute("INSERT INTO findings(ts,kind,severity,subject,score,details_json) VALUES(?,?,?,?,?,?)",(time.time(),kind,severity,subject,score,json.dumps(details,default=str)))
        self.receipt("finding",subject,{"kind":kind,"severity":severity,"score":score}); self.conn.commit()
    def nodes(self): return [dict(r) for r in self.conn.execute("SELECT * FROM nodes ORDER BY entity_id")]
    def edges(self): return [dict(r) for r in self.conn.execute("SELECT * FROM edges ORDER BY id")]
    def findings(self): return [dict(r) for r in self.conn.execute("SELECT kind,severity,subject,score,details_json FROM findings ORDER BY score DESC,id")]
    def verify_ledger(self):
        prev="GENESIS"; n=0
        for r in self.conn.execute("SELECT seq,kind,subject,payload_hash,prev_hash,entry_hash FROM ledger ORDER BY seq"):
            exp=digest({"kind":r["kind"],"subject":r["subject"],"payload_hash":r["payload_hash"],"prev_hash":prev})
            if r["prev_hash"]!=prev: return {"ok":False,"seq":r["seq"],"reason":"prev_hash_mismatch"}
            if r["entry_hash"]!=exp: return {"ok":False,"seq":r["seq"],"reason":"entry_hash_mismatch"}
            prev=r["entry_hash"]; n+=1
        return {"ok":True,"entries":n,"head":prev}
    def stats(self):
        return {"nodes":self.conn.execute("SELECT COUNT(*) n FROM nodes").fetchone()["n"],"edges":self.conn.execute("SELECT COUNT(*) n FROM edges").fetchone()["n"],"findings":self.conn.execute("SELECT COUNT(*) n FROM findings").fetchone()["n"],"ledger":self.verify_ledger(),"db_integrity":self.conn.execute("PRAGMA integrity_check").fetchone()[0]}
    def bundle(self,out):
        out=Path(out)
        with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
            for table in ["nodes","edges","findings","ledger"]:
                rows=[dict(r) for r in self.conn.execute(f"SELECT * FROM {table} ORDER BY 1")]
                z.writestr(f"{table}.json",json.dumps(rows,indent=2,default=str))
            z.writestr("manifest.json",json.dumps({"stats":self.stats(),"created":time.time()},indent=2))
        return {"bundle":str(out),"exists":out.exists()}

class FraudEngine:
    def __init__(self,store): self.store=store
    def load_graph(self,nodes,edges):
        for n in nodes: self.store.add_node(n)
        for e in edges: self.store.add_edge(e)
        return self.analyze()
    def analyze(self):
        nodes={n["entity_id"]:n for n in self.store.nodes()}
        edges=self.store.edges()
        proof=defaultdict(list); scores={}
        for n in nodes.values(): proof[n["proof_hash"]].append(n)
        def add(sub,kind,pts,details):
            scores.setdefault(sub,{"score":0,"reasons":[]})
            scores[sub]["score"]+=pts; scores[sub]["reasons"].append({"kind":kind,"points":pts,"details":details})
        for ph,group in proof.items():
            if ph and len(group)>1:
                for n in group: add(n["entity_id"],"shared_proof_hash",35,{"peers":[x["entity_id"] for x in group]})
        for n in nodes.values():
            if n["trust_score"]<0.25: add(n["entity_id"],"low_trust_score",25,{"trust_score":n["trust_score"]})
        incoming=defaultdict(list)
        for e in edges:
            incoming[e["target_id"]].append(e)
            if e["relation"]=="shadow_clone": add(e["target_id"],"shadow_clone_edge",60,e)
            if e["relation"]=="clone": add(e["target_id"],"clone_edge",30,e)
            s=nodes.get(e["source_id"]); t=nodes.get(e["target_id"])
            if s and t and s["entity_type"]!=t["entity_type"] and e["relation"] not in {"issuer","validator","witness","auditor"}:
                add(e["target_id"],"unvalidated_domain_crossing",40,e)
        for target,inc in incoming.items():
            issuers=[e for e in inc if e["relation"]=="issuer"]
            if len(issuers)>1: add(target,"multiple_issuers",20,{"issuers":[e["source_id"] for e in issuers]})
        out=[]
        for sub,data in scores.items():
            score=min(100,data["score"])
            sev="critical" if score>=75 else "high" if score>=50 else "medium" if score>=25 else "low"
            self.store.finding("fraud_anomaly",sev,sub,score,data)
            out.append({"subject":sub,"score":score,"severity":sev,"reasons":data["reasons"]})
        return {"subjects_scored":len(out),"findings":out}
