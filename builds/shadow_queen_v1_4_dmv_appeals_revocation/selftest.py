
from pathlib import Path
import tempfile
from shadowqueen.core import Store,ShadowQueenDMV,ObserverEvent
good={"person_id":"P-1","legal_name":"Good Person","address":"1 True Rd","dob":"1990-01-01","document_id":"D1"}
new={"person_id":"P-1","legal_name":"Good Person","address":"2 Better Rd","dob":"1990-01-01","document_id":"D1"}
with tempfile.TemporaryDirectory() as td:
    s=Store(Path(td)/"dmv.db"); dmv=ShadowQueenDMV(s,3)
    dmv.process([ObserverEvent.from_dict({"observer_id":"m1","record":good}),ObserverEvent.from_dict({"observer_id":"m2","record":good}),ObserverEvent.from_dict({"observer_id":"m3","record":good})])
    assert s.stats()["issued_identities"]==1
    s.create_appeal("A-1","P-1","address correction")
    result=dmv.appeal_review("A-1","P-1",[ObserverEvent.from_dict({"observer_id":"r1","record":new}),ObserverEvent.from_dict({"observer_id":"r2","record":new}),ObserverEvent.from_dict({"observer_id":"r3","record":new})])
    assert result["result"]=="restored", result
    reg=s.registry()[0]
    assert reg["status"]=="active"
    assert "2 better rd" in reg["address"]
    bundle=s.evidence_bundle(Path(td)/"evidence.zip")
    assert Path(bundle["bundle"]).exists()
    assert s.stats()["db_integrity"]=="ok"
print("SELFTEST PASS")
