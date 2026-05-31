import json, hashlib, sqlite3, time, zipfile
from pathlib import Path
from dataclasses import dataclass, field

def digest(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()

@dataclass(frozen=True)
class FederatedEvent:
    event_id: str
    origin_office: str
    event_type: str
    subject: str
    payload: dict = field(default_factory=dict)
    ts: float = 0.0
    event_hash: str = ""

    @classmethod
    def create(cls, origin, event_type, subject, payload=None):
        ts = time.time()
        payload = payload or {}
        base = {"origin_office": origin, "event_type": event_type, "subject": subject, "payload": payload, "ts": ts}
        eid = digest(base)
        eh = digest({**base, "event_id": eid})
        return cls(eid, origin, event_type, subject, payload, ts, eh)

    def verify(self):
        base = {"origin_office": self.origin_office, "event_type": self.event_type, "subject": self.subject, "payload": self.payload, "ts": self.ts}
        return self.event_id == digest(base) and self.event_hash == digest({**base, "event_id": self.event_id})

class Store:
    def __init__(self, path="replication.db", office_id="north"):
        self.office_id = office_id
        self.conn = sqlite3.connect(Path(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript('''
        CREATE TABLE IF NOT EXISTS events(event_id TEXT PRIMARY KEY, origin_office TEXT, event_type TEXT, subject TEXT, event_hash TEXT, ts REAL, payload_json TEXT, verified INTEGER, applied INTEGER);
        CREATE TABLE IF NOT EXISTS credentials(credential_id TEXT PRIMARY KEY, subject_id TEXT, credential_type TEXT, status TEXT, proof_hash TEXT, origin_office TEXT, last_event_id TEXT, version INTEGER, updated_ts REAL);
        CREATE TABLE IF NOT EXISTS mirrors(id INTEGER PRIMARY KEY, ts REAL, credential_id TEXT, office_id TEXT, status TEXT, version INTEGER, event_id TEXT, mirror_hash TEXT);
        CREATE TABLE IF NOT EXISTS conflicts(id INTEGER PRIMARY KEY, ts REAL, credential_id TEXT, kind TEXT, severity TEXT, status TEXT, details_json TEXT);
        CREATE TABLE IF NOT EXISTS outbox(id INTEGER PRIMARY KEY, ts REAL, event_id TEXT, target_office TEXT, status TEXT, attempts INTEGER, last_error TEXT);
        CREATE TABLE IF NOT EXISTS inbox(id INTEGER PRIMARY KEY, ts REAL, event_id TEXT, from_office TEXT, status TEXT, reason TEXT);
        CREATE TABLE IF NOT EXISTS audits(id INTEGER PRIMARY KEY, ts REAL, auditor TEXT, result TEXT, details_json TEXT);
        CREATE TABLE IF NOT EXISTS ledger(seq INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, kind TEXT, subject TEXT, payload_hash TEXT, prev_hash TEXT, entry_hash TEXT);
        ''')
        self.conn.commit()

    def last_hash(self):
        r = self.conn.execute("SELECT entry_hash FROM ledger ORDER BY seq DESC LIMIT 1").fetchone()
        return r["entry_hash"] if r else "GENESIS"

    def receipt(self, kind, subject, payload):
        prev = self.last_hash(); ph = digest(payload); eh = digest({"kind": kind, "subject": subject, "payload_hash": ph, "prev_hash": prev})
        self.conn.execute("INSERT INTO ledger(ts,kind,subject,payload_hash,prev_hash,entry_hash) VALUES(?,?,?,?,?,?)", (time.time(), kind, subject, ph, prev, eh))
        self.conn.commit(); return eh

    def verify_ledger(self):
        prev = "GENESIS"; n = 0
        for r in self.conn.execute("SELECT seq,kind,subject,payload_hash,prev_hash,entry_hash FROM ledger ORDER BY seq"):
            exp = digest({"kind": r["kind"], "subject": r["subject"], "payload_hash": r["payload_hash"], "prev_hash": prev})
            if r["prev_hash"] != prev: return {"ok": False, "seq": r["seq"], "reason": "prev_hash_mismatch"}
            if r["entry_hash"] != exp: return {"ok": False, "seq": r["seq"], "reason": "entry_hash_mismatch"}
            prev = r["entry_hash"]; n += 1
        return {"ok": True, "entries": n, "head": prev}

    def store_event(self, ev):
        ok = ev.verify()
        self.conn.execute("INSERT OR IGNORE INTO events VALUES(?,?,?,?,?,?,?,?,?)", (ev.event_id, ev.origin_office, ev.event_type, ev.subject, ev.event_hash, ev.ts, json.dumps(ev.payload), int(ok), 0))
        self.receipt("event_store", ev.event_id, {"verified": ok, "office": self.office_id, "type": ev.event_type})
        return ok

    def get_event(self, eid):
        r = self.conn.execute("SELECT * FROM events WHERE event_id=?", (eid,)).fetchone()
        if not r: return None
        return FederatedEvent(r["event_id"], r["origin_office"], r["event_type"], r["subject"], json.loads(r["payload_json"]), r["ts"], r["event_hash"])

    def conflict(self, cid, kind, severity, details):
        self.conn.execute("INSERT INTO conflicts(ts,credential_id,kind,severity,status,details_json) VALUES(?,?,?,?,?,?)", (time.time(), cid, kind, severity, "open", json.dumps(details, default=str)))
        self.receipt("conflict", cid, {"kind": kind, "severity": severity, "details": details})

    def credential(self, cid):
        r = self.conn.execute("SELECT * FROM credentials WHERE credential_id=?", (cid,)).fetchone()
        return dict(r) if r else None

    def credentials(self):
        return [dict(r) for r in self.conn.execute("SELECT * FROM credentials ORDER BY credential_id")]

    def apply_event(self, ev):
        if not ev.verify():
            self.conflict(ev.subject, "bad_event_hash", "high", {"event_id": ev.event_id})
            return {"applied": False, "reason": "bad_event_hash"}
        p = ev.payload; cid = p.get("credential_id", ev.subject); version = int(p.get("version", 1)); cur = self.credential(cid)
        if cur and version < int(cur["version"]):
            self.conflict(cid, "stale_event_version", "medium", {"current_version": cur["version"], "incoming_version": version, "event_id": ev.event_id})
            return {"applied": False, "reason": "stale_event_version"}
        if ev.event_type == "credential_issued":
            proof_hash = p.get("proof_hash", "")
            if cur and cur["proof_hash"] != proof_hash:
                self.conflict(cid, "same_credential_different_proof", "high", {"current": cur, "incoming": p})
                return {"applied": False, "reason": "proof_conflict"}
            self.conn.execute("INSERT OR REPLACE INTO credentials VALUES(?,?,?,?,?,?,?,?,?)", (cid, p.get("subject_id", ""), p.get("credential_type", "identity"), "active", proof_hash, ev.origin_office, ev.event_id, version, time.time()))
        else:
            sm = {"credential_suspended":"suspended", "credential_revoked":"revoked", "credential_expired":"expired", "credential_replaced":"replaced", "credential_renewed":"active"}
            if ev.event_type not in sm:
                self.conflict(cid, "unknown_event_type", "low", {"event_type": ev.event_type}); return {"applied": False, "reason": "unknown_event_type"}
            if not cur:
                self.conflict(cid, "missing_credential_for_transition", "medium", {"event_type": ev.event_type}); return {"applied": False, "reason": "missing_credential"}
            self.conn.execute("UPDATE credentials SET status=?, last_event_id=?, version=?, updated_ts=? WHERE credential_id=?", (sm[ev.event_type], ev.event_id, version, time.time(), cid))
        ns = self.credential(cid); mh = digest({"credential_id": cid, "office_id": self.office_id, "status": ns["status"], "version": ns["version"], "event_id": ev.event_id})
        self.conn.execute("INSERT INTO mirrors(ts,credential_id,office_id,status,version,event_id,mirror_hash) VALUES(?,?,?,?,?,?,?)", (time.time(), cid, self.office_id, ns["status"], ns["version"], ev.event_id, mh))
        self.conn.execute("UPDATE events SET applied=1 WHERE event_id=?", (ev.event_id,))
        self.receipt("event_applied", ev.event_id, {"credential_id": cid, "office": self.office_id, "version": version})
        self.conn.commit(); return {"applied": True, "credential_id": cid, "version": version, "status": ns["status"]}

    def publish(self, event_type, cid, payload, targets=None):
        ev = FederatedEvent.create(self.office_id, event_type, cid, payload); self.store_event(ev); self.apply_event(ev)
        for t in targets or []: self.conn.execute("INSERT INTO outbox(ts,event_id,target_office,status,attempts,last_error) VALUES(?,?,?,?,?,?)", (time.time(), ev.event_id, t, "queued", 0, ""))
        self.receipt("event_publish", ev.event_id, {"targets": targets or [], "type": event_type}); self.conn.commit(); return ev

    def receive(self, ev, from_office):
        if self.conn.execute("SELECT 1 FROM events WHERE event_id=?", (ev.event_id,)).fetchone():
            self.conn.execute("INSERT INTO inbox(ts,event_id,from_office,status,reason) VALUES(?,?,?,?,?)", (time.time(), ev.event_id, from_office, "duplicate", "already_seen")); self.receipt("duplicate_event", ev.event_id, {"from": from_office}); self.conn.commit(); return {"accepted": False, "status": "duplicate"}
        if not self.store_event(ev):
            self.conn.execute("INSERT INTO inbox(ts,event_id,from_office,status,reason) VALUES(?,?,?,?,?)", (time.time(), ev.event_id, from_office, "rejected", "bad_hash")); self.conn.commit(); return {"accepted": False, "status": "rejected"}
        applied = self.apply_event(ev); self.conn.execute("INSERT INTO inbox(ts,event_id,from_office,status,reason) VALUES(?,?,?,?,?)", (time.time(), ev.event_id, from_office, "accepted", "")); self.conn.commit(); return {"accepted": True, "status": "accepted", "applied": applied}

    def pending(self): return [dict(r) for r in self.conn.execute("SELECT * FROM outbox WHERE status='queued' ORDER BY id")]
    def mark_delivery(self, eid, target, status, details=None):
        self.conn.execute("UPDATE outbox SET status=?, attempts=attempts+1, last_error=? WHERE event_id=? AND target_office=?", (status, (details or {}).get("error", ""), eid, target)); self.receipt("delivery", eid, {"target": target, "status": status, "details": details or {}}); self.conn.commit()

    def audit_convergence(self, peers, auditor="auditor"):
        local = {c["credential_id"]: c for c in self.credentials()}; report = {"office": self.office_id, "peer_drift": {}}; result = "pass"
        for peer in peers:
            remote = {c["credential_id"]: c for c in peer.credentials()}; drift = []
            for cid, c in local.items():
                r = remote.get(cid)
                if not r: drift.append({"credential_id": cid, "kind": "missing_remote"})
                elif (c["status"], c["version"], c["proof_hash"]) != (r["status"], r["version"], r["proof_hash"]): drift.append({"credential_id": cid, "kind": "state_mismatch"})
            for cid in remote:
                if cid not in local: drift.append({"credential_id": cid, "kind": "missing_local"})
            report["peer_drift"][peer.office_id] = drift
            if drift: result = "warning"
        self.conn.execute("INSERT INTO audits(ts,auditor,result,details_json) VALUES(?,?,?,?)", (time.time(), auditor, result, json.dumps(report)))
        self.receipt("convergence_audit", auditor, {"result": result, "report": report}); self.conn.commit(); return {"result": result, "report": report}

    def stats(self):
        return {"office_id": self.office_id, "events": self.conn.execute("SELECT COUNT(*) n FROM events").fetchone()["n"], "credentials": self.conn.execute("SELECT COUNT(*) n FROM credentials").fetchone()["n"], "mirrors": self.conn.execute("SELECT COUNT(*) n FROM mirrors").fetchone()["n"], "conflicts": self.conn.execute("SELECT COUNT(*) n FROM conflicts").fetchone()["n"], "outbox": self.conn.execute("SELECT COUNT(*) n FROM outbox").fetchone()["n"], "inbox": self.conn.execute("SELECT COUNT(*) n FROM inbox").fetchone()["n"], "audits": self.conn.execute("SELECT COUNT(*) n FROM audits").fetchone()["n"], "ledger": self.verify_ledger(), "db_integrity": self.conn.execute("PRAGMA integrity_check").fetchone()[0]}

    def bundle(self, out):
        out = Path(out)
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for t in ["events", "credentials", "mirrors", "conflicts", "outbox", "inbox", "audits", "ledger"]:
                rows = [dict(r) for r in self.conn.execute(f"SELECT * FROM {t} ORDER BY 1")]
                z.writestr(f"{t}.json", json.dumps(rows, indent=2, default=str))
            z.writestr("manifest.json", json.dumps({"stats": self.stats(), "created": time.time()}, indent=2))
        return {"bundle": str(out), "exists": out.exists()}

class Replicator:
    def __init__(self, store): self.store = store
    def issue(self, cid, subject_id, credential_type="identity", proof_hash="", targets=None, version=1): return self.store.publish("credential_issued", cid, {"credential_id": cid, "subject_id": subject_id, "credential_type": credential_type, "proof_hash": proof_hash, "version": version}, targets or [])
    def transition(self, cid, event_type, targets=None, version=1): return self.store.publish(event_type, cid, {"credential_id": cid, "version": version}, targets or [])
    def deliver_to(self, target, eid):
        ev = self.store.get_event(eid)
        if not ev: return {"delivered": False, "reason": "missing_event"}
        res = target.receive(ev, self.store.office_id); self.store.mark_delivery(eid, target.office_id, "delivered" if res.get("accepted") else res.get("status", "failed"), res); return {"delivered": res.get("accepted", False), "result": res}
    def replay(self, peers):
        out=[]
        for row in self.store.pending():
            peer = peers.get(row["target_office"])
            if not peer: self.store.mark_delivery(row["event_id"], row["target_office"], "no_peer", {"error":"peer unavailable"}); continue
            out.append(self.deliver_to(peer, row["event_id"]))
        return out
