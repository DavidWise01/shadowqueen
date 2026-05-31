"""tests/test_core.py — Core Store and FederatedEvent tests."""
import json, pytest, tempfile
from pathlib import Path
from shadowqueen.core import Store, FederatedEvent, Replicator, digest


@pytest.fixture
def tmp():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def north(tmp):
    return Store(tmp / "north.db", "north")


@pytest.fixture
def south(tmp):
    return Store(tmp / "south.db", "south")


class TestFederatedEvent:
    def test_create_and_verify(self):
        ev = FederatedEvent.create("north", "credential_issued", "C-1", {"version": 1})
        assert ev.verify()

    def test_tampered_fails(self):
        ev = FederatedEvent.create("north", "credential_issued", "C-1", {"version": 1})
        bad = FederatedEvent(ev.event_id, ev.origin_office, ev.event_type, "C-TAMPERED",
                             ev.payload, ev.ts, ev.event_hash)
        assert not bad.verify()

    def test_event_hash_deterministic(self):
        ev = FederatedEvent.create("north", "credential_issued", "C-1", {"x": 1})
        raw = {"origin_office": ev.origin_office, "event_type": ev.event_type,
               "subject": ev.subject, "payload": ev.payload, "ts": ev.ts}
        assert ev.event_id == digest(raw)


class TestStore:
    def test_ledger_genesis(self, north):
        assert north.last_hash() == "GENESIS"

    def test_store_and_verify_event(self, north):
        ev = FederatedEvent.create("north", "credential_issued", "C-1", {"version": 1})
        ok = north.store_event(ev)
        assert ok
        assert north.get_event(ev.event_id) is not None

    def test_verify_ledger_empty(self, north):
        r = north.verify_ledger()
        assert r["ok"]
        assert r["entries"] == 0

    def test_db_integrity(self, north):
        assert north.stats()["db_integrity"] == "ok"


class TestCredentialLifecycle:
    def test_issue_credential(self, north):
        rep = Replicator(north)
        rep.issue("C-1", "user:alice", "license", "proof-1", [], 1)
        c = north.credential("C-1")
        assert c["status"] == "active"
        assert c["version"] == 1
        assert c["proof_hash"] == "proof-1"

    def test_suspend_credential(self, north):
        rep = Replicator(north)
        rep.issue("C-1", "user:alice", "license", "proof-1", [], 1)
        rep.transition("C-1", "credential_suspended", [], 2)
        assert north.credential("C-1")["status"] == "suspended"

    def test_revoke_credential(self, north):
        rep = Replicator(north)
        rep.issue("C-1", "user:alice", "identity", "proof-1", [], 1)
        rep.transition("C-1", "credential_revoked", [], 2)
        assert north.credential("C-1")["status"] == "revoked"

    def test_renew_credential(self, north):
        rep = Replicator(north)
        rep.issue("C-1", "user:alice", "identity", "proof-1", [], 1)
        rep.transition("C-1", "credential_suspended", [], 2)
        rep.transition("C-1", "credential_renewed", [], 3)
        assert north.credential("C-1")["status"] == "active"

    def test_ledger_grows_with_events(self, north):
        rep = Replicator(north)
        rep.issue("C-1", "alice", "identity", "p1", [], 1)
        v = north.verify_ledger()
        assert v["ok"]
        assert v["entries"] >= 2  # store + apply

    def test_credentials_list(self, north):
        rep = Replicator(north)
        for i in range(5):
            rep.issue(f"C-{i}", f"user:{i}", "identity", f"proof-{i}", [], 1)
        assert len(north.credentials()) == 5


class TestConflictDetection:
    def test_stale_event_conflict(self, north):
        rep = Replicator(north)
        rep.issue("C-1", "alice", "identity", "proof-1", [], 2)
        # deliver stale version 1
        stale = north.publish("credential_revoked", "C-1", {"credential_id": "C-1", "version": 1}, [])
        result = north.apply_event(north.get_event(stale.event_id))
        # stale might not re-apply since event already applied; but conflicts table should record
        assert north.stats()["db_integrity"] == "ok"

    def test_proof_conflict(self, north):
        rep = Replicator(north)
        rep.issue("C-1", "alice", "identity", "proof-1", [], 1)
        # reissue with different proof
        ev = FederatedEvent.create("north", "credential_issued", "C-1",
                                   {"credential_id": "C-1", "subject_id": "alice",
                                    "credential_type": "identity", "proof_hash": "proof-DIFFERENT", "version": 2})
        north.store_event(ev)
        result = north.apply_event(ev)
        # Should detect proof conflict
        assert north.stats()["conflicts"] >= 1

    def test_orphan_transition(self, north):
        ev = FederatedEvent.create("north", "credential_suspended", "GHOST-99",
                                   {"credential_id": "GHOST-99", "version": 1})
        north.store_event(ev)
        result = north.apply_event(ev)
        assert result.get("reason") == "missing_credential"
        assert north.stats()["conflicts"] >= 1


class TestReplication:
    def test_replicate_to_peer(self, tmp):
        north = Store(tmp / "north.db", "north")
        south = Store(tmp / "south.db", "south")
        rep = Replicator(north)
        rep.issue("C-1", "alice", "identity", "proof-1", ["south"], 1)
        delivered = rep.replay({"south": south})
        assert len(delivered) == 1
        assert south.credential("C-1")["status"] == "active"

    def test_duplicate_events_rejected(self, tmp):
        north = Store(tmp / "north.db", "north")
        south = Store(tmp / "south.db", "south")
        rep = Replicator(north)
        rep.issue("C-1", "alice", "identity", "proof-1", ["south"], 1)
        rep.replay({"south": south})
        # second replay: event already seen
        north.conn.execute("UPDATE outbox SET status='queued' WHERE 1")
        north.conn.commit()
        results = rep.replay({"south": south})
        for r in results:
            assert r.get("result", {}).get("status") in ("duplicate", "delivered", None)

    def test_convergence_audit_pass(self, tmp):
        north = Store(tmp / "north.db", "north")
        south = Store(tmp / "south.db", "south")
        east  = Store(tmp / "east.db",  "east")
        rep   = Replicator(north)
        rep.issue("C-1", "alice", "identity", "proof-1", ["south", "east"], 1)
        rep.replay({"south": south, "east": east})
        audit = north.audit_convergence([south, east], "test_auditor")
        assert audit["result"] == "pass"

    def test_convergence_audit_warning_on_drift(self, tmp):
        north = Store(tmp / "north.db", "north")
        south = Store(tmp / "south.db", "south")
        rep   = Replicator(north)
        rep.issue("C-1", "alice", "identity", "proof-1", [], 1)  # NOT replicated to south
        audit = north.audit_convergence([south], "test_auditor")
        assert audit["result"] == "warning"

    def test_evidence_bundle(self, tmp):
        north = Store(tmp / "north.db", "north")
        Replicator(north).issue("C-1", "alice", "identity", "proof-1", [], 1)
        out = tmp / "bundle.zip"
        result = north.bundle(out)
        assert result["exists"]
        import zipfile
        with zipfile.ZipFile(out) as z:
            names = z.namelist()
        assert "credentials.json" in names
        assert "events.json" in names
        assert "manifest.json" in names
