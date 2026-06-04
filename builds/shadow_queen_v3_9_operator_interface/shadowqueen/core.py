
import json, hashlib, sqlite3, time, zipfile
from pathlib import Path

def digest(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()

class OperatorInterface:
    def __init__(self, path="operator.db", operator="operator:root"):
        self.operator = operator
        self.conn = sqlite3.connect(Path(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS dashboard_cards(id TEXT PRIMARY KEY, title TEXT, category TEXT, severity TEXT, status TEXT, payload TEXT);
        CREATE TABLE IF NOT EXISTS queues(id TEXT PRIMARY KEY, name TEXT, item_count INTEGER, severity TEXT, payload TEXT);
        CREATE TABLE IF NOT EXISTS reviews(id TEXT PRIMARY KEY, kind TEXT, subject TEXT, status TEXT, decision TEXT, details TEXT);
        CREATE TABLE IF NOT EXISTS operator_actions(id INTEGER PRIMARY KEY, ts REAL, operator TEXT, action TEXT, subject TEXT, result TEXT, details TEXT);
        CREATE TABLE IF NOT EXISTS release_checks(id TEXT PRIMARY KEY, name TEXT, status TEXT, score REAL, details TEXT);
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
        prev = "GENESIS"
        n = 0
        for r in self.conn.execute("SELECT seq,kind,subject,payload_hash,prev_hash,entry_hash FROM ledger ORDER BY seq"):
            exp = digest({"kind": r["kind"], "subject": r["subject"], "payload_hash": r["payload_hash"], "prev_hash": prev})
            if r["prev_hash"] != prev:
                return {"ok": False, "seq": r["seq"], "reason": "prev_hash_mismatch"}
            if r["entry_hash"] != exp:
                return {"ok": False, "seq": r["seq"], "reason": "entry_hash_mismatch"}
            prev = r["entry_hash"]
            n += 1
        return {"ok": True, "entries": n, "head": prev}

    def action(self, action, subject, result="ok", details=None):
        self.conn.execute(
            "INSERT INTO operator_actions(ts,operator,action,subject,result,details) VALUES(?,?,?,?,?,?)",
            (time.time(), self.operator, action, subject, result, json.dumps(details or {}, default=str))
        )
        self.receipt("operator_action", subject, {"operator": self.operator, "action": action, "result": result})

    def card(self, title, category, severity="low", status="open", payload=None):
        cid = "card:" + digest({"title": title, "category": category, "payload": payload or {}})[:16]
        self.conn.execute("INSERT OR REPLACE INTO dashboard_cards VALUES(?,?,?,?,?,?)",
                          (cid, title, category, severity, status, json.dumps(payload or {}, default=str)))
        self.action("dashboard_card", cid, "ok", {"title": title, "category": category})
        self.conn.commit()
        return {"card": cid, "title": title, "severity": severity}

    def queue(self, name, items, severity="medium"):
        qid = "queue:" + digest({"name": name})[:16]
        self.conn.execute("INSERT OR REPLACE INTO queues VALUES(?,?,?,?,?)",
                          (qid, name, len(items), severity, json.dumps(items, default=str)))
        self.action("queue_updated", qid, "ok", {"name": name, "count": len(items)})
        self.conn.commit()
        return {"queue": qid, "name": name, "item_count": len(items), "severity": severity}

    def open_review(self, kind, subject, details=None):
        rid = "review:" + digest({"kind": kind, "subject": subject, "ts": time.time()})[:16]
        self.conn.execute("INSERT INTO reviews VALUES(?,?,?,?,?,?)",
                          (rid, kind, subject, "open", "", json.dumps(details or {}, default=str)))
        self.action("review_opened", rid, "ok", {"kind": kind, "subject": subject})
        self.conn.commit()
        return {"review": rid, "status": "open"}

    def decide_review(self, review_id, decision, details=None):
        self.conn.execute("UPDATE reviews SET status='closed', decision=?, details=? WHERE id=?",
                          (decision, json.dumps(details or {}, default=str), review_id))
        self.action("review_decided", review_id, decision, details or {})
        self.conn.commit()
        return {"review": review_id, "decision": decision, "status": "closed"}

    def release_check(self, name, status, score, details=None):
        cid = "check:" + digest({"name": name})[:16]
        self.conn.execute("INSERT OR REPLACE INTO release_checks VALUES(?,?,?,?,?)",
                          (cid, name, status, float(score), json.dumps(details or {}, default=str)))
        self.action("release_check", cid, status, {"name": name, "score": score})
        self.conn.commit()
        return {"check": cid, "name": name, "status": status, "score": score}

    def dashboard(self):
        cards = [dict(r) for r in self.conn.execute("SELECT * FROM dashboard_cards ORDER BY severity DESC,title")]
        queues = [dict(r) for r in self.conn.execute("SELECT * FROM queues ORDER BY severity DESC,name")]
        reviews = [dict(r) for r in self.conn.execute("SELECT * FROM reviews ORDER BY id")]
        checks = [dict(r) for r in self.conn.execute("SELECT * FROM release_checks ORDER BY name")]
        fail = [c for c in checks if c["status"] not in ("pass", "ok")]
        open_reviews = [r for r in reviews if r["status"] == "open"]
        status = "blocked" if fail else "review" if open_reviews else "ready"
        return {
            "operator": self.operator,
            "status": status,
            "cards": len(cards),
            "queues": len(queues),
            "open_reviews": len(open_reviews),
            "release_checks": checks,
            "ledger": self.verify_ledger(),
        }

    def stats(self):
        return {
            "operator": self.operator,
            "cards": self.conn.execute("SELECT COUNT(*) n FROM dashboard_cards").fetchone()["n"],
            "queues": self.conn.execute("SELECT COUNT(*) n FROM queues").fetchone()["n"],
            "reviews": self.conn.execute("SELECT COUNT(*) n FROM reviews").fetchone()["n"],
            "actions": self.conn.execute("SELECT COUNT(*) n FROM operator_actions").fetchone()["n"],
            "release_checks": self.conn.execute("SELECT COUNT(*) n FROM release_checks").fetchone()["n"],
            "ledger": self.verify_ledger(),
            "db_integrity": self.conn.execute("PRAGMA integrity_check").fetchone()[0],
        }

    def bundle(self, out):
        out = Path(out)
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for t in ["dashboard_cards", "queues", "reviews", "operator_actions", "release_checks", "ledger"]:
                rows = [dict(r) for r in self.conn.execute(f"SELECT * FROM {t} ORDER BY 1")]
                z.writestr(f"{t}.json", json.dumps(rows, indent=2, default=str))
            z.writestr("dashboard.json", json.dumps(self.dashboard(), indent=2, default=str))
            z.writestr("manifest.json", json.dumps({"stats": self.stats(), "created": time.time()}, indent=2))
        return {"bundle": str(out), "exists": out.exists()}

def seed_demo(ui):
    ui.card("Federation Health", "ops", "medium", "open", {"offices": 4, "degraded": ["west"]})
    ui.card("Investigation Queue", "cases", "high", "open", {"open_cases": 3})
    ui.card("Authority Reviews", "authority", "medium", "open", {"pending": 1})
    ui.queue("Open Investigations", [{"case": "case:synthetic"}, {"case": "case:credential"}], "high")
    ui.queue("Authority Decisions", [{"review": "agent:wallet"}], "medium")
    r = ui.open_review("credential_disagreement", "credential:C-1", {"north": "active", "east": "revoked"})
    ui.decide_review(r["review"], "route_to_investigation", {"reason": "cross-office mismatch"})
    ui.release_check("ledger_integrity", "pass", 100, {})
    ui.release_check("selftests", "pass", 100, {})
    ui.release_check("open_critical_reviews", "pass", 95, {})
    return ui.dashboard()
