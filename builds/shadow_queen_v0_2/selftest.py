
from pathlib import Path
import tempfile
from shadowqueen.core import Event, ShadowQueen, Store

q=ShadowQueen()
assert q.classify(Event("a","call",phase="+1"))["action"]=="allow"
assert q.classify(Event("s","call",phase="-1"))["action"]=="quarantine"
assert q.classify(Event("p","session",layer="L5",features={"payload_read_attempt":True}))["action"]=="quarantine"
assert q.classify(Event("w","io",wiggle_sequence="++++"))["action"]=="quarantine"
q.classify(Event("parent","call",phase="-1"))
assert q.classify(Event("child","call",phase="0",parent_id="parent"))["action"]=="track"

with tempfile.TemporaryDirectory() as td:
    s=Store(Path(td)/"sq.db")
    e=Event("persist","call",phase="-1")
    d=q.classify(e); s.record(e,d)
    assert s.stats()["events"]==1
    assert s.stats()["fingerprint_memory"]>=1
print("SELFTEST PASS")
