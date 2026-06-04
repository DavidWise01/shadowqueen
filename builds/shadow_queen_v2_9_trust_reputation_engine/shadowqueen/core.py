
import json, hashlib, sqlite3, time, zipfile
from pathlib import Path

def digest(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()

class TrustStore:
    def __init__(self, path="trust.db", office="north"):
        self.office = office
        self.conn = sqlite3.connect(Path(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS subjects(subject_id TEXT PRIMARY KEY, subject_type TEXT, office TEXT, base_score REAL, metadata_json TEXT, updated_ts REAL);
        CREATE TABLE IF NOT EXISTS signals(id INTEGER PRIMARY KEY, ts REAL, subject_id TEXT, signal_type TEXT, source TEXT, weight REAL, confidence REAL, details_json TEXT);
        CREATE TABLE IF NOT EXISTS trust_scores(subject_id TEXT PRIMARY KEY, subject_type TEXT, score REAL, severity TEXT, confidence REAL, reasons_json TEXT, updated_ts REAL);
        CREATE TABLE IF NOT EXISTS reputation_edges(id INTEGER PRIMARY KEY, ts REAL, source_id TEXT, target_id TEXT, relation TEXT, trust_delta REAL, details_json TEXT);
        CREATE TABLE IF NOT EXISTS trust_audits(id INTEGER PRIMARY KEY, ts REAL, auditor TEXT, result TEXT, details_json TEXT);
        CREATE TABLE IF NOT EXISTS ledger(seq INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT, subject TEXT, payload_hash TEXT, prev_hash TEXT, entry_hash TEXT);
        """)
        self.conn.commit()

    def last_hash(self):
        r = self.conn.execute("SELECT entry_hash FROM ledger ORDER BY seq DESC LIMIT 1").fetchone()
        return r["entry_hash"] if r else "GENESIS"

    def receipt(self, kind, subject, payload):
        prev = self.last_hash()
        ph = digest(payload)
        eh = digest({"kind": kind, "subject": subject, "payload_hash": ph, "prev_hash": prev})
        self.conn.execute("INSERT INTO ledger(kind,subject,payload_hash,prev_hash,entry_hash) VALUES(?,?,?,?,?)", (kind, subject, ph, prev, eh))
        self.conn.commit()

    def verify_ledger(self):
        prev = "GENESIS"; n = 0
        for r in self.conn.execute("SELECT seq,kind,subject,payload_hash,prev_hash,entry_hash FROM ledger ORDER BY seq"):
            exp = digest({"kind": r["kind"], "subject": r["subject"], "payload_hash": r["payload_hash"], "prev_hash": prev})
            if r["prev_hash"] != prev: return {"ok": False, "seq": r["seq"], "reason": "prev_hash_mismatch"}
            if r["entry_hash"] != exp: return {"ok": False, "seq": r["seq"], "reason": "entry_hash_mismatch"}
            prev = r["entry_hash"]; n += 1
        return {"ok": True, "entries": n, "head": prev}

    def add_subject(self, subject_id, subject_type, base_score=50.0, metadata=None):
        self.conn.execute("INSERT OR REPLACE INTO subjects VALUES(?,?,?,?,?,?)", (subject_id, subject_type, self.office, float(base_score), json.dumps(metadata or {}), time.time()))
        self.receipt("subject", subject_id, {"type": subject_type, "base_score": base_score})
        return {"subject_id": subject_id, "subject_type": subject_type, "base_score": base_score}

    def add_signal(self, subject_id, signal_type, source="local", weight=0.0, confidence=1.0, details=None):
        self.conn.execute("INSERT INTO signals(ts,subject_id,signal_type,source,weight,confidence,details_json) VALUES(?,?,?,?,?,?,?)", (time.time(), subject_id, signal_type, source, float(weight), float(confidence), json.dumps(details or {}, default=str)))
        self.receipt("signal", subject_id, {"signal_type": signal_type, "weight": weight, "confidence": confidence})
        return {"subject_id": subject_id, "signal_type": signal_type, "weight": weight, "confidence": confidence}

    def add_reputation_edge(self, source_id, target_id, relation, trust_delta=0.0, details=None):
        self.conn.execute("INSERT INTO reputation_edges(ts,source_id,target_id,relation,trust_delta,details_json) VALUES(?,?,?,?,?,?)", (time.time(), source_id, target_id, relation, float(trust_delta), json.dumps(details or {}, default=str)))
        self.receipt("reputation_edge", f"{source_id}->{target_id}", {"relation": relation, "trust_delta": trust_delta})
        return {"source_id": source_id, "target_id": target_id, "relation": relation, "trust_delta": trust_delta}

    def subjects(self): return [dict(r) for r in self.conn.execute("SELECT * FROM subjects ORDER BY subject_id")]
    def signals_for(self, subject_id): return [dict(r) for r in self.conn.execute("SELECT * FROM signals WHERE subject_id=? ORDER BY id", (subject_id,))]
    def edges_for_target(self, subject_id): return [dict(r) for r in self.conn.execute("SELECT * FROM reputation_edges WHERE target_id=? ORDER BY id", (subject_id,))]

    def compute_subject(self, subject):
        sid = subject["subject_id"]; score = float(subject["base_score"]); reasons=[]; total_conf=0.0; conf_count=0
        for sig in self.signals_for(sid):
            delta = float(sig["weight"]) * float(sig["confidence"]); score += delta
            total_conf += float(sig["confidence"]); conf_count += 1
            reasons.append({"kind":"signal","signal_type":sig["signal_type"],"source":sig["source"],"weight":sig["weight"],"confidence":sig["confidence"],"delta":round(delta,4),"details":json.loads(sig["details_json"] or "{}")})
        for edge in self.edges_for_target(sid):
            delta=float(edge["trust_delta"]); score += delta
            reasons.append({"kind":"reputation_edge","source_id":edge["source_id"],"relation":edge["relation"],"delta":delta,"details":json.loads(edge["details_json"] or "{}")})
        score=max(0.0,min(100.0,score)); confidence=round(total_conf/conf_count,4) if conf_count else 0.5
        severity = "trusted" if score>=80 else "watch" if score>=60 else "review" if score>=40 else "quarantine"
        self.conn.execute("INSERT OR REPLACE INTO trust_scores VALUES(?,?,?,?,?,?,?)", (sid, subject["subject_type"], score, severity, confidence, json.dumps(reasons, default=str), time.time()))
        self.receipt("trust_score", sid, {"score":score,"severity":severity,"confidence":confidence})
        return {"subject_id":sid,"subject_type":subject["subject_type"],"score":score,"severity":severity,"confidence":confidence,"reasons":reasons}

    def compute_all(self):
        out=[self.compute_subject(s) for s in self.subjects()]; self.conn.commit(); return out
    def scores(self): return [dict(r) for r in self.conn.execute("SELECT subject_id,subject_type,score,severity,confidence,reasons_json FROM trust_scores ORDER BY score DESC")]

    def ingest_fraud_findings(self, findings):
        mapping={"possible_duplicate_identity":-35,"synthetic_identity_signal":-45,"credential_stuffing_signal":-40,"suspicious_address_cluster":-30,"unknown_relationship_type":-20,"self_loop_relationship":-25}
        added=[]
        for f in findings:
            subject=f.get("subject") or f.get("subject_id"); kind=f.get("kind","fraud_signal"); raw=float(f.get("score",50)); weight=mapping.get(kind,-min(50,raw/2))
            if subject: added.append(self.add_signal(subject,kind,source="fraud_engine",weight=weight,confidence=0.9,details=f))
        return {"signals_added":len(added),"signals":added}

    def audit(self, auditor="auditor"):
        scores=self.scores(); quarantine=len([s for s in scores if s["severity"]=="quarantine"]); review=len([s for s in scores if s["severity"]=="review"]); trusted=len([s for s in scores if s["severity"]=="trusted"])
        result="critical" if quarantine else "warning" if review else "pass"; details={"quarantine":quarantine,"review":review,"trusted":trusted,"subjects":len(scores)}
        self.conn.execute("INSERT INTO trust_audits(ts,auditor,result,details_json) VALUES(?,?,?,?)", (time.time(), auditor, result, json.dumps(details)))
        self.receipt("trust_audit", auditor, details); self.conn.commit(); return {"result":result,"details":details}

    def stats(self):
        return {"office":self.office,"subjects":self.conn.execute("SELECT COUNT(*) n FROM subjects").fetchone()["n"],"signals":self.conn.execute("SELECT COUNT(*) n FROM signals").fetchone()["n"],"scores":self.conn.execute("SELECT COUNT(*) n FROM trust_scores").fetchone()["n"],"edges":self.conn.execute("SELECT COUNT(*) n FROM reputation_edges").fetchone()["n"],"audits":self.conn.execute("SELECT COUNT(*) n FROM trust_audits").fetchone()["n"],"ledger":self.verify_ledger(),"db_integrity":self.conn.execute("PRAGMA integrity_check").fetchone()[0]}

    def bundle(self, out):
        out=Path(out)
        with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
            for t in ["subjects","signals","trust_scores","reputation_edges","trust_audits","ledger"]:
                rows=[dict(r) for r in self.conn.execute(f"SELECT * FROM {t} ORDER BY 1")]
                z.writestr(f"{t}.json",json.dumps(rows,indent=2,default=str))
            z.writestr("manifest.json",json.dumps({"stats":self.stats(),"created":time.time()},indent=2))
        return {"bundle":str(out),"exists":out.exists()}

def seed_demo(store):
    store.add_subject("person:root","identity",85,{"domain":"carbon"})
    store.add_subject("credential:C-1","credential",80,{"type":"license"})
    store.add_subject("office:north","office",75,{})
    store.add_subject("person:synthetic","identity",45,{"domain":"carbon"})
    store.add_signal("person:root","valid_proof","identity_proof",15,0.95,{"proof":"document+address"})
    store.add_signal("credential:C-1","clean_lifecycle","credential_lifecycle",10,0.9,{})
    store.add_signal("office:north","ledger_verified","audit",10,1.0,{})
    store.add_signal("person:synthetic","synthetic_identity_signal","fraud_engine",-45,0.9,{})
    store.add_reputation_edge("office:north","credential:C-1","issuer_reputation",5,{})
    store.add_reputation_edge("credential:C-1","person:root","credential_supports_identity",8,{})
