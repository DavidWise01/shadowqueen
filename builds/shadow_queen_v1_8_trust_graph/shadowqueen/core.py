
import json, hashlib, sqlite3, time, zipfile
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Any

def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()

@dataclass(frozen=True)
class IdentityProof:
    entity_id: str
    entity_type: str  # carbon | silicon
    identity_hash: str
    address_hash: str = ""
    document_hash: str = ""
    biometric_placeholder: str = ""
    trust_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls,d):
        et=str(d.get("entity_type","")).lower()
        if et not in {"carbon","silicon"}:
            raise ValueError("entity_type must be carbon or silicon")
        return cls(
            entity_id=str(d["entity_id"]),
            entity_type=et,
            identity_hash=str(d.get("identity_hash","")),
            address_hash=str(d.get("address_hash","")),
            document_hash=str(d.get("document_hash","")),
            biometric_placeholder=str(d.get("biometric_placeholder","")),
            trust_score=float(d.get("trust_score",0.0)),
            metadata=dict(d.get("metadata",{}))
        )

    def fingerprint(self):
        return digest({
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "identity_hash": self.identity_hash,
            "address_hash": self.address_hash,
            "document_hash": self.document_hash,
            "biometric_placeholder": self.biometric_placeholder,
        })

@dataclass(frozen=True)
class TrustEdge:
    source_id: str
    target_id: str
    relation: str  # parent child issuer validator witness auditor clone shadow_clone
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls,d):
        return cls(str(d["source_id"]),str(d["target_id"]),str(d["relation"]),float(d.get("confidence",1.0)),dict(d.get("metadata",{})))

    def fingerprint(self):
        return digest({
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation": self.relation,
            "confidence": round(self.confidence,4),
            "metadata": self.metadata
        })

class Store:
    def __init__(self,path="shadowqueen_trust_graph.db"):
        self.conn=sqlite3.connect(Path(path)); self.conn.row_factory=sqlite3.Row
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS identity_nodes(entity_id TEXT PRIMARY KEY,entity_type TEXT,fingerprint TEXT,trust_score REAL,metadata_json TEXT,created_ts REAL,updated_ts REAL);
        CREATE TABLE IF NOT EXISTS trust_edges(id INTEGER PRIMARY KEY,ts REAL,source_id TEXT,target_id TEXT,relation TEXT,confidence REAL,fingerprint TEXT,metadata_json TEXT);
        CREATE TABLE IF NOT EXISTS graph_findings(id INTEGER PRIMARY KEY,ts REAL,kind TEXT,severity TEXT,subject TEXT,details_json TEXT);
        CREATE TABLE IF NOT EXISTS trust_ledger(seq INTEGER PRIMARY KEY AUTOINCREMENT,ts REAL,kind TEXT,subject TEXT,payload_hash TEXT,prev_hash TEXT,entry_hash TEXT,receipt_json TEXT);
        """); self.conn.commit()

    def last_hash(self):
        r=self.conn.execute("SELECT entry_hash FROM trust_ledger ORDER BY seq DESC LIMIT 1").fetchone()
        return r["entry_hash"] if r else "GENESIS"

    def receipt(self,kind,subject,payload):
        prev=self.last_hash(); ph=digest(payload); eh=digest({"kind":kind,"subject":subject,"payload_hash":ph,"prev_hash":prev})
        rec={"kind":kind,"subject":subject,"payload_hash":ph,"prev_hash":prev,"entry_hash":eh,"ts":time.time()}
        self.conn.execute("INSERT INTO trust_ledger(ts,kind,subject,payload_hash,prev_hash,entry_hash,receipt_json) VALUES(?,?,?,?,?,?,?)",(rec["ts"],kind,subject,ph,prev,eh,json.dumps(rec,sort_keys=True)))
        self.conn.commit(); return rec

    def add_identity(self,proof):
        now=time.time(); fp=proof.fingerprint()
        self.conn.execute("""INSERT INTO identity_nodes(entity_id,entity_type,fingerprint,trust_score,metadata_json,created_ts,updated_ts)
        VALUES(?,?,?,?,?,?,?)
        ON CONFLICT(entity_id) DO UPDATE SET entity_type=excluded.entity_type,fingerprint=excluded.fingerprint,trust_score=excluded.trust_score,metadata_json=excluded.metadata_json,updated_ts=excluded.updated_ts""",
        (proof.entity_id,proof.entity_type,fp,proof.trust_score,json.dumps(proof.metadata),now,now))
        self.receipt("identity_node",proof.entity_id,{"entity_type":proof.entity_type,"fingerprint":fp,"trust_score":proof.trust_score})
        self.conn.commit()
        return {"entity_id":proof.entity_id,"fingerprint":fp}

    def add_edge(self,edge):
        fp=edge.fingerprint()
        self.conn.execute("INSERT INTO trust_edges(ts,source_id,target_id,relation,confidence,fingerprint,metadata_json) VALUES(?,?,?,?,?,?,?)",(time.time(),edge.source_id,edge.target_id,edge.relation,edge.confidence,fp,json.dumps(edge.metadata)))
        self.receipt("trust_edge",f"{edge.source_id}->{edge.target_id}",{"relation":edge.relation,"confidence":edge.confidence,"fingerprint":fp})
        self.conn.commit()
        return {"edge":f"{edge.source_id}->{edge.target_id}","relation":edge.relation,"fingerprint":fp}

    def finding(self,kind,severity,subject,details):
        self.conn.execute("INSERT INTO graph_findings(ts,kind,severity,subject,details_json) VALUES(?,?,?,?,?)",(time.time(),kind,severity,subject,json.dumps(details,default=str)))
        self.receipt("graph_finding",subject,{"kind":kind,"severity":severity,"details":details})
        self.conn.commit()

    def nodes(self):
        return [dict(r) for r in self.conn.execute("SELECT entity_id,entity_type,fingerprint,trust_score FROM identity_nodes ORDER BY entity_id")]

    def edges(self):
        return [dict(r) for r in self.conn.execute("SELECT source_id,target_id,relation,confidence,fingerprint FROM trust_edges ORDER BY id")]

    def findings(self):
        return [dict(r) for r in self.conn.execute("SELECT kind,severity,subject,details_json FROM graph_findings ORDER BY id")]

    def verify_ledger(self):
        prev="GENESIS"; n=0
        for r in self.conn.execute("SELECT seq,kind,subject,payload_hash,prev_hash,entry_hash FROM trust_ledger ORDER BY seq"):
            expected=digest({"kind":r["kind"],"subject":r["subject"],"payload_hash":r["payload_hash"],"prev_hash":prev})
            if r["prev_hash"]!=prev: return {"ok":False,"seq":r["seq"],"reason":"prev_hash_mismatch"}
            if r["entry_hash"]!=expected: return {"ok":False,"seq":r["seq"],"reason":"entry_hash_mismatch"}
            prev=r["entry_hash"]; n+=1
        return {"ok":True,"entries":n,"head":prev}

    def stats(self):
        return {
            "nodes": self.conn.execute("SELECT COUNT(*) n FROM identity_nodes").fetchone()["n"],
            "edges": self.conn.execute("SELECT COUNT(*) n FROM trust_edges").fetchone()["n"],
            "findings": self.conn.execute("SELECT COUNT(*) n FROM graph_findings").fetchone()["n"],
            "ledger": self.verify_ledger(),
            "db_integrity": self.conn.execute("PRAGMA integrity_check").fetchone()[0],
        }

    def bundle(self,out):
        out=Path(out)
        with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
            for table in ["identity_nodes","trust_edges","graph_findings","trust_ledger"]:
                rows=[dict(r) for r in self.conn.execute(f"SELECT * FROM {table} ORDER BY 1")]
                z.writestr(f"{table}.json",json.dumps(rows,indent=2,default=str))
            z.writestr("manifest.json",json.dumps({"stats":self.stats(),"created":time.time()},indent=2))
        return {"bundle":str(out),"exists":out.exists()}

class TrustGraph:
    def __init__(self,store):
        self.store=store

    def ingest(self,nodes,edges):
        for n in nodes: self.store.add_identity(n)
        for e in edges: self.store.add_edge(e)
        return self.analyze()

    def analyze(self):
        nodes={r["entity_id"]:r for r in self.store.nodes()}
        edges=self.store.edges()
        clone_edges=[e for e in edges if e["relation"] in {"clone","shadow_clone"}]
        missing=[]
        for e in edges:
            if e["source_id"] not in nodes or e["target_id"] not in nodes:
                missing.append(e)
        if missing:
            self.store.finding("missing_node_reference","high","graph",{"edges":missing})
        for e in clone_edges:
            sev="critical" if e["relation"]=="shadow_clone" else "medium"
            self.store.finding(e["relation"],sev,e["target_id"],e)
        # Carbon/Silicon crossing is allowed but should be explicit via validator/witness/issuer.
        crossings=[]
        for e in edges:
            s=nodes.get(e["source_id"]); t=nodes.get(e["target_id"])
            if s and t and s["entity_type"]!=t["entity_type"] and e["relation"] not in {"issuer","validator","witness","auditor"}:
                crossings.append(e)
        if crossings:
            self.store.finding("domain_crossing_unvalidated","high","carbon_silicon_boundary",{"edges":crossings})
        return {"nodes":len(nodes),"edges":len(edges),"clone_edges":len(clone_edges),"missing_refs":len(missing),"domain_crossings":len(crossings)}

    def lineage(self,entity_id):
        edges=self.store.edges()
        reverse={}
        for e in edges:
            reverse.setdefault(e["target_id"],[]).append(e)
        path=[]; seen=set(); cur=entity_id
        while cur in reverse and cur not in seen:
            seen.add(cur)
            e=reverse[cur][0]
            path.append(e)
            cur=e["source_id"]
        return path
