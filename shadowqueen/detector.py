"""
detector.py — Shadow Queen AI Threat Detection Engine
Zero external dependencies. Pure statistical analysis over the credential event stream.

Threat classes:
  T1  VELOCITY_SPIKE        — burst of events from one origin in a short window
  T2  VERSION_ROLLBACK      — incoming version lower than current (replay attack)
  T3  PROOF_CYCLING         — same credential reissued with different proofs (key compromise)
  T4  RAPID_STATE_CYCLE     — credential toggling states faster than policy allows
  T5  ORPHAN_TRANSITION     — transition event for a non-existent credential
  T6  STALE_FLOOD           — flood of stale/duplicate events (noise injection)
  T7  CONFLICT_CLUSTER      — multiple conflict types on same credential (coordinated attack)
  T8  UNVERIFIED_EVENT_RATE — high fraction of events failing hash verification
"""

import json
import time
from dataclasses import dataclass, field
from collections import defaultdict
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────────────
#  THREAT SIGNAL
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Threat:
    code:       str                          # T1..T8
    severity:   str                          # critical / high / medium / low
    credential_id: str = ""
    origin:     str = ""
    detected_ts: float = field(default_factory=time.time)
    evidence:   dict = field(default_factory=dict)
    score:      float = 0.0                  # 0.0 – 1.0 normalised risk

    def to_dict(self):
        return {
            "code":           self.code,
            "severity":       self.severity,
            "credential_id":  self.credential_id,
            "origin":         self.origin,
            "detected_ts":    self.detected_ts,
            "evidence":       self.evidence,
            "score":          round(self.score, 4),
        }


# ─────────────────────────────────────────────────────────────────────────────
#  DETECTOR
# ─────────────────────────────────────────────────────────────────────────────

class ThreatDetector:
    """
    Stateless scanner: call scan(store) → list[Threat].
    Reads directly from a Store's SQLite connection.
    No side effects on the store — detection is read-only.
    """

    # Tuneable thresholds
    VELOCITY_WINDOW_SECONDS = 60
    VELOCITY_SPIKE_THRESHOLD = 20          # events from one origin in window
    RAPID_CYCLE_WINDOW_SECONDS = 300
    RAPID_CYCLE_THRESHOLD = 4              # state changes on one credential
    STALE_FLOOD_THRESHOLD = 10             # stale conflicts from same origin
    UNVERIFIED_RATE_THRESHOLD = 0.15       # 15% unverified events → alert

    def scan(self, store) -> list[Threat]:
        threats = []
        conn = store.conn
        now = time.time()

        # ── T1: Velocity spike ────────────────────────────────────────────────
        window_start = now - self.VELOCITY_WINDOW_SECONDS
        rows = conn.execute(
            "SELECT origin_office, COUNT(*) n FROM events WHERE ts>=? GROUP BY origin_office",
            (window_start,)
        ).fetchall()
        for r in rows:
            if r[1] >= self.VELOCITY_SPIKE_THRESHOLD:
                score = min(1.0, r[1] / (self.VELOCITY_SPIKE_THRESHOLD * 3))
                threats.append(Threat(
                    code="T1", severity="high" if score > 0.7 else "medium",
                    origin=r[0], score=score,
                    evidence={"events_in_window": r[1], "window_seconds": self.VELOCITY_WINDOW_SECONDS},
                ))

        # ── T2: Version rollback (check conflicts table for stale_event_version) ──
        stale = conn.execute(
            "SELECT credential_id, COUNT(*) as cnt FROM conflicts WHERE kind='stale_event_version' GROUP BY credential_id"
        ).fetchall()
        for r in stale:
            threats.append(Threat(
                code="T2", severity="high", credential_id=r[0],
                score=min(1.0, r[1] / 5),
                evidence={"stale_count": r[1]},
            ))

        # ── T3: Proof cycling ─────────────────────────────────────────────────
        proof_conflicts = conn.execute(
            "SELECT credential_id FROM conflicts WHERE kind='same_credential_different_proof'"
        ).fetchall()
        for r in proof_conflicts:
            threats.append(Threat(
                code="T3", severity="critical", credential_id=r[0],
                score=0.95,
                evidence={"kind": "proof_hash_mismatch_on_reissue"},
            ))

        # ── T4: Rapid state cycling ───────────────────────────────────────────
        cycle_start = now - self.RAPID_CYCLE_WINDOW_SECONDS
        rows = conn.execute(
            "SELECT subject, COUNT(*) as cnt FROM events WHERE ts>=? AND event_type!='credential_issued' GROUP BY subject",
            (cycle_start,)
        ).fetchall()
        for r in rows:
            if r[1] >= self.RAPID_CYCLE_THRESHOLD:
                score = min(1.0, r[1] / (self.RAPID_CYCLE_THRESHOLD * 4))
                threats.append(Threat(
                    code="T4", severity="high" if score > 0.6 else "medium",
                    credential_id=r[0], score=score,
                    evidence={"transitions_in_window": r[1], "window_seconds": self.RAPID_CYCLE_WINDOW_SECONDS},
                ))

        # ── T5: Orphan transitions ────────────────────────────────────────────
        orphans = conn.execute(
            "SELECT credential_id FROM conflicts WHERE kind='missing_credential_for_transition'"
        ).fetchall()
        for r in orphans:
            threats.append(Threat(
                code="T5", severity="medium", credential_id=r[0],
                score=0.65,
                evidence={"kind": "transition_without_prior_issuance"},
            ))

        # ── T6: Stale flood ───────────────────────────────────────────────────
        stale_flood = conn.execute(
            "SELECT credential_id, COUNT(*) as cnt FROM conflicts WHERE kind='stale_event_version' GROUP BY credential_id HAVING cnt>=?",
            (self.STALE_FLOOD_THRESHOLD,)
        ).fetchall()
        for r in stale_flood:
            score = min(1.0, r[1] / (self.STALE_FLOOD_THRESHOLD * 2))
            threats.append(Threat(
                code="T6", severity="high", credential_id=r[0], score=score,
                evidence={"stale_event_count": r[1]},
            ))

        # ── T7: Conflict cluster ──────────────────────────────────────────────
        cluster = conn.execute(
            "SELECT credential_id, COUNT(DISTINCT kind) as kinds, COUNT(*) as total FROM conflicts GROUP BY credential_id"
        ).fetchall()
        for r in cluster:
            if r[1] >= 3:
                score = min(1.0, r[1] / 6)
                threats.append(Threat(
                    code="T7", severity="critical" if r[1] >= 4 else "high",
                    credential_id=r[0], score=score,
                    evidence={"distinct_conflict_types": r[1], "total_conflicts": r[2]},
                ))

        # ── T8: Unverified event rate ─────────────────────────────────────────
        total = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        unverified = conn.execute("SELECT COUNT(*) FROM events WHERE verified=0").fetchone()[0]
        if total > 0:
            rate = unverified / total
            if rate >= self.UNVERIFIED_RATE_THRESHOLD:
                score = min(1.0, rate / 0.5)
                threats.append(Threat(
                    code="T8", severity="critical" if rate > 0.3 else "high",
                    score=score,
                    evidence={"unverified": unverified, "total": total, "rate": round(rate, 4)},
                ))

        # Deduplicate (same code + credential_id) keeping highest score
        seen: dict[tuple, Threat] = {}
        for t in threats:
            k = (t.code, t.credential_id)
            if k not in seen or t.score > seen[k].score:
                seen[k] = t

        return sorted(seen.values(), key=lambda x: -x.score)

    def scan_to_dict(self, store) -> dict:
        threats = self.scan(store)
        counts = defaultdict(int)
        for t in threats:
            counts[t.severity] += 1
        risk = max((t.score for t in threats), default=0.0)
        level = "clean" if not threats else (
            "critical" if counts["critical"] else
            "high" if counts["high"] else
            "medium" if counts["medium"] else "low"
        )
        return {
            "office": store.office_id,
            "scanned_ts": time.time(),
            "threat_level": level,
            "risk_score": round(risk, 4),
            "threat_count": len(threats),
            "by_severity": dict(counts),
            "threats": [t.to_dict() for t in threats],
        }
