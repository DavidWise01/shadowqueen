
from pathlib import Path
import tempfile
from shadowqueen.core import Event,Store,ShadowQueen
with tempfile.TemporaryDirectory() as td:
    s=Store(Path(td)/"sq.db"); q=ShadowQueen(s)
    for _ in range(3):
        e=Event.from_dict({"source_id":"a","event_type":"process_snapshot"})
        d=q.classify(e,learn_mode=True); s.record(e,d,learn=True)
    known=q.classify(Event.from_dict({"source_id":"a","event_type":"process_snapshot"}))
    new=q.classify(Event.from_dict({"source_id":"b","event_type":"process_snapshot"}))
    assert known["action"]=="allow", known
    assert new["action"]=="track", new
    assert new["reason"]=="baseline_drift_new", new
print("SELFTEST PASS")
