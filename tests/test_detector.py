"""tests/test_detector.py — AI threat detection tests."""
import tempfile, time, pytest
from pathlib import Path
from shadowqueen.core import Store, Replicator, FederatedEvent
from shadowqueen.detector import ThreatDetector


@pytest.fixture
def tmp():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


class TestThreatDetector:
    def test_clean_store_no_threats(self, tmp):
        st = Store(tmp / "x.db", "north")
        rep = Replicator(st)
        rep.issue("C-1", "alice", "identity", "proof-1", [], 1)
        result = ThreatDetector().scan_to_dict(st)
        assert result["threat_level"] == "clean"
        assert result["threat_count"] == 0

    def test_proof_cycling_detected(self, tmp):
        st = Store(tmp / "x.db", "north")
        rep = Replicator(st)
        rep.issue("C-1", "alice", "identity", "proof-1", [], 1)
        # Reissue with different proof — T3
        ev = FederatedEvent.create("north", "credential_issued", "C-1", {
            "credential_id": "C-1", "subject_id": "alice",
            "credential_type": "identity", "proof_hash": "proof-EVIL", "version": 2,
        })
        st.store_event(ev); st.apply_event(ev)
        result = ThreatDetector().scan_to_dict(st)
        codes = {t["code"] for t in result["threats"]}
        assert "T3" in codes
        assert result["threat_level"] in ("critical", "high")

    def test_orphan_transition_detected(self, tmp):
        st = Store(tmp / "x.db", "north")
        # Transition without issuance — T5
        ev = FederatedEvent.create("north", "credential_suspended", "GHOST",
                                   {"credential_id": "GHOST", "version": 1})
        st.store_event(ev); st.apply_event(ev)
        result = ThreatDetector().scan_to_dict(st)
        codes = {t["code"] for t in result["threats"]}
        assert "T5" in codes

    def test_unverified_event_detected(self, tmp):
        st = Store(tmp / "x.db", "north")
        # Force-insert unverified events
        import sqlite3, hashlib, json
        for i in range(10):
            st.conn.execute(
                "INSERT OR IGNORE INTO events VALUES(?,?,?,?,?,?,?,?,?)",
                (f"bad-{i}", "rogue", "credential_issued", f"C-{i}", "badhash",
                 time.time(), "{}", 0, 0)
            )
        st.conn.commit()
        result = ThreatDetector().scan_to_dict(st)
        codes = {t["code"] for t in result["threats"]}
        assert "T8" in codes

    def test_result_structure(self, tmp):
        st = Store(tmp / "x.db", "north")
        result = ThreatDetector().scan_to_dict(st)
        assert "threat_level" in result
        assert "risk_score" in result
        assert "threats" in result
        assert isinstance(result["threats"], list)
        assert 0.0 <= result["risk_score"] <= 1.0
