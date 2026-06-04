
import json, hashlib, sqlite3, time, zipfile
from pathlib import Path

def digest(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()

class DMV:
    def __init__(self, path="dmv_beta.db", office="north"):
        self.office = office
        self.conn = sqlite3.connect(Path(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS citizens(id TEXT PRIMARY KEY, name TEXT, dob TEXT, domain TEXT, trust_score REAL, status TEXT, attrs TEXT);
        CREATE TABLE IF NOT EXISTS credentials(id TEXT PRIMARY KEY, citizen_id TEXT, type TEXT, status TEXT, version INTEGER, proof_hash TEXT, expires_ts REAL);
        CREATE TABLE IF NOT EXISTS workflows(id TEXT PRIMARY KEY, citizen_id TEXT, kind TEXT, status TEXT, step TEXT, details TEXT, created_ts REAL, updated_ts REAL);
        CREATE TABLE IF NOT EXISTS investigations(id TEXT PRIMARY KEY, subject TEXT, kind TEXT, severity TEXT, status TEXT, details TEXT, created_ts REAL, updated_ts REAL);
        CREATE TABLE IF NOT EXISTS audit_log(id INTEGER PRIMARY KEY, ts REAL, actor TEXT, action TEXT, subject TEXT, result TEXT, details TEXT);
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
        return eh

    def audit(self, actor, action, subject, result, details=None):
        self.conn.execute(
            "INSERT INTO audit_log(ts,actor,action,subject,result,details) VALUES(?,?,?,?,?,?)",
            (time.time(), actor, action, subject, result, json.dumps(details or {}, default=str)),
        )
        self.receipt("audit", subject, {"actor": actor, "action": action, "result": result})

    def verify_ledger(self):
        prev = "GENESIS"; n = 0
        for r in self.conn.execute("SELECT seq,kind,subject,payload_hash,prev_hash,entry_hash FROM ledger ORDER BY seq"):
            exp = digest({"kind": r["kind"], "subject": r["subject"], "payload_hash": r["payload_hash"], "prev_hash": prev})
            if r["prev_hash"] != prev:
                return {"ok": False, "seq": r["seq"], "reason": "prev_hash_mismatch"}
            if r["entry_hash"] != exp:
                return {"ok": False, "seq": r["seq"], "reason": "entry_hash_mismatch"}
            prev = r["entry_hash"]; n += 1
        return {"ok": True, "entries": n, "head": prev}

    def citizen_id(self, name, dob, domain):
        return "citizen:" + digest({"name": name.lower().strip(), "dob": dob, "domain": domain})[:16]

    def enroll_citizen(self, name, dob, domain="carbon", trust_score=50, attrs=None, actor="citizen"):
        cid = self.citizen_id(name, dob, domain)
        self.conn.execute("INSERT OR REPLACE INTO citizens VALUES(?,?,?,?,?,?,?)",
            (cid, name, dob, domain, float(trust_score), "active", json.dumps(attrs or {})))
        self.audit(actor, "enroll_citizen", cid, "ok", {"trust_score": trust_score})
        self.conn.commit()
        return {"citizen_id": cid, "status": "active", "trust_score": trust_score}

    def citizen(self, citizen_id):
        r = self.conn.execute("SELECT * FROM citizens WHERE id=?", (citizen_id,)).fetchone()
        return dict(r) if r else None

    def credential(self, cred_id):
        r = self.conn.execute("SELECT * FROM credentials WHERE id=?", (cred_id,)).fetchone()
        return dict(r) if r else None

    def open_workflow(self, citizen_id, kind, details=None, actor="citizen"):
        wid = "workflow:" + digest({"citizen_id": citizen_id, "kind": kind, "ts": time.time()})[:16]
        self.conn.execute("INSERT INTO workflows VALUES(?,?,?,?,?,?,?,?)",
            (wid, citizen_id, kind, "open", "submitted", json.dumps(details or {}), time.time(), time.time()))
        self.audit(actor, "open_workflow", wid, "ok", {"kind": kind, "citizen_id": citizen_id})
        self.conn.commit()
        return {"workflow_id": wid, "status": "open", "step": "submitted"}

    def trust_gate(self, citizen_id, minimum=60):
        c = self.citizen(citizen_id)
        if not c:
            return {"allowed": False, "reason": "missing_citizen"}
        if float(c["trust_score"]) < minimum:
            return {"allowed": False, "reason": "trust_score_below_minimum", "trust_score": c["trust_score"], "minimum": minimum}
        return {"allowed": True, "trust_score": c["trust_score"], "minimum": minimum}

    def issue_credential(self, citizen_id, cred_type="license", proof_hash="", ttl_days=365, actor="registrar"):
        gate = self.trust_gate(citizen_id, 60)
        if not gate["allowed"]:
            inv = self.open_investigation(citizen_id, "issuance_denied", "medium", gate, actor)
            self.audit(actor, "issue_credential", citizen_id, "denied", {"gate": gate, "investigation": inv})
            return {"ok": False, "denied": gate, "investigation": inv}
        cred_id = f"credential:{cred_type}:{digest({'citizen_id': citizen_id, 'proof_hash': proof_hash, 'ts': time.time()})[:12]}"
        self.conn.execute("INSERT INTO credentials VALUES(?,?,?,?,?,?,?)",
            (cred_id, citizen_id, cred_type, "active", 1, proof_hash, time.time() + ttl_days * 86400))
        self.audit(actor, "issue_credential", cred_id, "ok", {"citizen_id": citizen_id, "type": cred_type})
        self.conn.commit()
        return {"ok": True, "credential_id": cred_id, "status": "active"}

    def renew_credential(self, cred_id, actor="registrar"):
        cred = self.credential(cred_id)
        if not cred:
            return {"ok": False, "reason": "missing_credential"}
        gate = self.trust_gate(cred["citizen_id"], 55)
        if not gate["allowed"]:
            inv = self.open_investigation(cred["citizen_id"], "renewal_denied", "medium", gate, actor)
            return {"ok": False, "denied": gate, "investigation": inv}
        self.conn.execute("UPDATE credentials SET version=?, status=?, expires_ts=? WHERE id=?",
                          (int(cred["version"]) + 1, "active", time.time() + 365 * 86400, cred_id))
        self.audit(actor, "renew_credential", cred_id, "ok", {"version": int(cred["version"]) + 1})
        self.conn.commit()
        return {"ok": True, "credential_id": cred_id, "status": "active", "version": int(cred["version"]) + 1}

    def revoke_credential(self, cred_id, reason="policy", actor="auditor"):
        cred = self.credential(cred_id)
        if not cred:
            return {"ok": False, "reason": "missing_credential"}
        self.conn.execute("UPDATE credentials SET status=? WHERE id=?", ("revoked", cred_id))
        inv = self.open_investigation(cred_id, "credential_revoked", "high", {"reason": reason}, actor)
        self.audit(actor, "revoke_credential", cred_id, "ok", {"reason": reason, "investigation": inv})
        self.conn.commit()
        return {"ok": True, "credential_id": cred_id, "status": "revoked", "investigation": inv}

    def open_investigation(self, subject, kind, severity, details=None, actor="system"):
        iid = "case:" + digest({"subject": subject, "kind": kind, "ts": time.time()})[:16]
        self.conn.execute("INSERT INTO investigations VALUES(?,?,?,?,?,?,?,?)",
            (iid, subject, kind, severity, "open", json.dumps(details or {}, default=str), time.time(), time.time()))
        self.audit(actor, "open_investigation", iid, "ok", {"subject": subject, "kind": kind, "severity": severity})
        self.conn.commit()
        return {"case_id": iid, "status": "open", "severity": severity}

    def close_investigation(self, case_id, result="resolved", actor="auditor"):
        self.conn.execute("UPDATE investigations SET status=?, updated_ts=? WHERE id=?", (result, time.time(), case_id))
        self.audit(actor, "close_investigation", case_id, result, {})
        self.conn.commit()
        return {"case_id": case_id, "status": result}

    def portal_summary(self, citizen_id):
        c = self.citizen(citizen_id)
        creds = [dict(r) for r in self.conn.execute("SELECT * FROM credentials WHERE citizen_id=? ORDER BY id", (citizen_id,))]
        workflows = [dict(r) for r in self.conn.execute("SELECT * FROM workflows WHERE citizen_id=? ORDER BY created_ts", (citizen_id,))]
        cases = [dict(r) for r in self.conn.execute("SELECT * FROM investigations WHERE subject=? ORDER BY created_ts", (citizen_id,))]
        return {"citizen": c, "credentials": creds, "workflows": workflows, "investigations": cases}

    def office_queue(self):
        return {
            "open_workflows": [dict(r) for r in self.conn.execute("SELECT * FROM workflows WHERE status='open' ORDER BY created_ts")],
            "open_investigations": [dict(r) for r in self.conn.execute("SELECT * FROM investigations WHERE status='open' ORDER BY created_ts")],
        }

    def stats(self):
        return {
            "office": self.office,
            "citizens": self.conn.execute("SELECT COUNT(*) n FROM citizens").fetchone()["n"],
            "credentials": self.conn.execute("SELECT COUNT(*) n FROM credentials").fetchone()["n"],
            "workflows": self.conn.execute("SELECT COUNT(*) n FROM workflows").fetchone()["n"],
            "investigations": self.conn.execute("SELECT COUNT(*) n FROM investigations").fetchone()["n"],
            "audit_log": self.conn.execute("SELECT COUNT(*) n FROM audit_log").fetchone()["n"],
            "ledger": self.verify_ledger(),
            "db_integrity": self.conn.execute("PRAGMA integrity_check").fetchone()[0],
        }

    def bundle(self, out):
        out = Path(out)
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for t in ["citizens", "credentials", "workflows", "investigations", "audit_log", "ledger"]:
                rows = [dict(r) for r in self.conn.execute(f"SELECT * FROM {t} ORDER BY 1")]
                z.writestr(f"{t}.json", json.dumps(rows, indent=2, default=str))
            z.writestr("manifest.json", json.dumps({"stats": self.stats(), "created": time.time()}, indent=2))
        return {"bundle": str(out), "exists": out.exists()}

def seed_demo(dmv):
    good = dmv.enroll_citizen("Root User", "1981-06-21", "carbon", 88, actor="demo")
    weak = dmv.enroll_citizen("Synthetic User", "2000-01-01", "carbon", 25, actor="demo")
    dmv.open_workflow(good["citizen_id"], "license_application", {"channel": "citizen_portal"}, "citizen")
    issued = dmv.issue_credential(good["citizen_id"], "license", "proof-good", actor="registrar")
    denied = dmv.issue_credential(weak["citizen_id"], "license", "proof-weak", actor="registrar")
    if issued.get("ok"):
        dmv.renew_credential(issued["credential_id"], actor="registrar")
    return {"good": good, "weak": weak, "issued": issued, "denied": denied}
