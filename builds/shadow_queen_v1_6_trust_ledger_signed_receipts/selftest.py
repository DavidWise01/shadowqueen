
from pathlib import Path
import tempfile
from shadowqueen.core import Store,ObserverEvent,ConsensusDMV,FederationManager,ExternalAuditor,IdentityRecord
record={"person_id":"P-1","legal_name":"Good Person","address":"1 True Rd","dob":"1990-01-01","document_id":"D1"}
with tempfile.TemporaryDirectory() as td:
    s=Store(Path(td)/"dmv.db","north")
    ConsensusDMV(s,3).process([ObserverEvent.from_dict({"observer_id":"n1","record":record}),ObserverEvent.from_dict({"observer_id":"n2","record":record}),ObserverEvent.from_dict({"observer_id":"n3","record":record})])
    assert s.stats()["issued_identities"]==1
    remote=dict(s.registry()[0]); bad=IdentityRecord.from_dict({"person_id":"P-1","legal_name":"Good Person","address":"2 Conflict Rd","dob":"1990-01-01","document_id":"D1"})
    remote["address"]="2 conflict rd"; remote["fingerprint"]=bad.fingerprint()
    FederationManager(s).compare([remote],"south")
    audit=ExternalAuditor(s,"auditor-x").review()
    assert audit["result"]=="warning"
    assert s.verify_ledger()["ok"] is True
    bundle=s.bundle(Path(td)/"evidence.zip")
    assert Path(bundle["bundle"]).exists()
    assert s.stats()["db_integrity"]=="ok"
print("SELFTEST PASS")
