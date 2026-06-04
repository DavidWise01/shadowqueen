
from pathlib import Path
import tempfile
from shadowqueen.core import Store,ShadowQueenDMV,ObserverEvent
good={"person_id":"P-1","legal_name":"Good Person","address":"1 True Rd","dob":"1990-01-01","document_id":"D1"}
bad={"person_id":"P-2","legal_name":"Bad Person","address":"2 False Rd","dob":"1991-01-01","document_id":"D2"}
bad_alt={"person_id":"P-2","legal_name":"Bad Person","address":"3 False Rd","dob":"1991-01-01","document_id":"D2"}
raw=[{"observer_id":"m1","role":"clerk","record":good},{"observer_id":"m2","role":"address","record":good},{"observer_id":"m3","role":"document","record":good},{"observer_id":"m1","role":"clerk","record":bad},{"observer_id":"m2","role":"address","record":bad_alt},{"observer_id":"m3","role":"document","record":bad}]
with tempfile.TemporaryDirectory() as td:
    s=Store(Path(td)/"dmv.db"); dmv=ShadowQueenDMV(s,quorum=3)
    decisions=dmv.process([ObserverEvent.from_dict(x) for x in raw])
    by={d["person_id"]:d for d in decisions}
    assert by["P-1"]["action"]=="issue_identity", by["P-1"]
    assert by["P-2"]["action"]=="quarantine", by["P-2"]
    st=s.stats()
    assert st["issued_identities"]==1
    assert st["consensus_decisions"]==2
    assert st["db_integrity"]=="ok"
print("SELFTEST PASS")
