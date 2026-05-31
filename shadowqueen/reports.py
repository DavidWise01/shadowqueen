"""
reports.py — Compliance report generation for Shadow Queen
Produces SOC2-ready, point-in-time audit evidence.
"""

import json
import time
from pathlib import Path
from .detector import ThreatDetector


class ReportGenerator:
    """Generate compliance and operational reports from a Store."""

    def __init__(self, store):
        self.store = store
        self.detector = ThreatDetector()

    # ── Ledger integrity report ───────────────────────────────────────────────
    def ledger_integrity(self) -> dict:
        result = self.store.verify_ledger()
        stats  = self.store.stats()
        return {
            "report_type": "ledger_integrity",
            "office":      self.store.office_id,
            "generated":   time.time(),
            "ledger":      result,
            "events":      stats["events"],
            "credentials": stats["credentials"],
            "conflicts":   stats["conflicts"],
            "verdict":     "PASS" if result["ok"] else "FAIL",
            "note":        (
                "Ledger chain intact — all entry hashes verified sequentially."
                if result["ok"] else
                f"Chain broken at seq {result.get('seq')} ({result.get('reason')})."
            ),
        }

    # ── Credential inventory ──────────────────────────────────────────────────
    def credential_inventory(self) -> dict:
        creds   = self.store.credentials()
        by_type = {}
        by_status = {}
        for c in creds:
            by_type[c["credential_type"]] = by_type.get(c["credential_type"], 0) + 1
            by_status[c["status"]] = by_status.get(c["status"], 0) + 1
        return {
            "report_type":   "credential_inventory",
            "office":        self.store.office_id,
            "generated":     time.time(),
            "total":         len(creds),
            "by_type":       by_type,
            "by_status":     by_status,
            "credentials":   creds,
        }

    # ── Threat scan report ────────────────────────────────────────────────────
    def threat_scan(self) -> dict:
        result = self.detector.scan_to_dict(self.store)
        result["report_type"] = "threat_scan"
        result["generated"]   = time.time()
        return result

    # ── Conflict summary ──────────────────────────────────────────────────────
    def conflict_summary(self) -> dict:
        rows = [
            dict(r) for r in self.store.conn.execute(
                "SELECT kind, severity, COUNT(*) n, MAX(ts) last_ts FROM conflicts GROUP BY kind, severity ORDER BY n DESC"
            )
        ]
        return {
            "report_type":    "conflict_summary",
            "office":         self.store.office_id,
            "generated":      time.time(),
            "total_conflicts": sum(r["n"] for r in rows),
            "by_kind":        rows,
        }

    # ── Full compliance bundle ─────────────────────────────────────────────────
    def compliance_report(self, peers=None) -> dict:
        report = {
            "report_type":    "compliance_full",
            "office":         self.store.office_id,
            "generated":      time.time(),
            "ledger":         self.ledger_integrity(),
            "credentials":    self.credential_inventory(),
            "threats":        self.threat_scan(),
            "conflicts":      self.conflict_summary(),
        }
        if peers:
            audit = self.store.audit_convergence(peers, auditor="compliance_report")
            report["convergence"] = audit
        return report

    # ── Write report to file ──────────────────────────────────────────────────
    def save(self, report: dict, path: Path) -> Path:
        path = Path(path)
        path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
        return path
